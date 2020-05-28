# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 13:40:18 2020

@author: Alex
"""
import os,glob
import arcpy
import csv
import datetime
import random
import re
import logging
import tkFileDialog
import tkinter as tk
from tkinter import messagebox



class CheckShpFile():
    """
    - Проверка точек на наложение и дублирование как в миссинг так и в плантид
    - Проверка на пустые значения в class и variety
    - заполение пустых значений в класс
    - подсчет и создание лог файла
    """

    def create_log(self,message,error = False, count = False ):
        """
        создает лог файл с отчетами об функциях и инструментах
        ----------------------------------
        message : str
            тексе ошибки которая будет внесенна в лог файл
        
        error : boolean
            по умолчанию лог записывается как info если поставить значени True то будет записываться как ошибка
        """
        name = "CheckSHPfiles"
        if count:
            name = "CountPOINTS"
        logpath = os.path.join(logfolder, "LogFiles")
        if not os.path.exists(logpath):os.makedirs(logpath)
        now = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d")
        logfile = os.path.join(logpath,"{0}_{1}.log".format(date,name))
        logging.basicConfig(filename=logfile, level=logging.INFO,format='%(asctime)s -%(message)s')
        if error:
            logging.error(message)
            return
        logging.info(message)
        return
    
    
    def get_fid_from_filename(self,filename):
    
        fid_regex = re.compile("\d\d\d\d-[\d]{1,2}-[\d]{1,2} (?P<fid>[\d]+) ")
        farm_ids = fid_regex.findall(filename)
    
        if farm_ids:
            farm_id = int(farm_ids[0])
            return farm_id
        else:
            raise ValueError("Could not determine farm id.")
    
    
    
    def get_total_points (self, path, log = False):
        """
        return total points in shp
        """
        total = int(arcpy.GetCount_management(path)[0])
        if log:
            message = "In {0} Total = {1}".format(os.path.basename(path), total)
            self.create_log(message, count = True )
        
        return total
    
    
    def get_count_log(self,shp,atribute = "variety",query = '#'):
        """
        shp : str
            path to shp file
        ------------------------
        return 
            запись в лог файл
        """
        curs = arcpy.da.SearchCursor(shp,atribute,query)
        lst = [row for row in curs]
        count = dict( (l, lst.count(l) ) for l in set(lst))
        message = "In {0} = {1}/n Total = {2}".format(os.path.basename(shp), count, self.get_total_points(shp))
        self.create_log(message, count = True)
        return 
    
    
    def check_identcal(self,shp):
        """
        Check shp file for doubl click on points, to avoide two or more points on the same place
        Parameters
        ----------
        shp : str
           Path to shp file
           
        Returns
        -------
        delete identical points in shp file 
        
        """
        inputpoints = self.get_total_points(shp)
        arcpy.DeleteIdentical_management(shp, "Shape", "0.2 Meters")
        output = inputpoints - self.get_total_points(shp)
        if output > 0:
            message = 'Check identical points In {0} was delete =  {1} points'.format(os.path.basename(shp),output)
            self.create_log(message)
        
        return 
    
    
    
    
    
    def find_layer(self,pathtoflight, fid = '', parametr = '',typef = 'shp',block = ''):
        """
        Parameters:
            folder takes the name of the folder in flight (tree count, registered)
            parameter take the name of an object (VNIR for tif, miss for missing trees)
            typef taking the type of file (tif, shp)
        Return:
            path to file
        """
        layer = glob.glob(os.path.join(pathtoflight, "*{0}**{1}*.{2}").format(str(fid), parametr, typef))
        if len(layer) == 0:
            print ('For fid {0} there is no file {1} '.format(str(fid), typef))
            layer = ''
            return  layer
            
        if len(layer) > 1:
            root = tk.Tk()
            root.filename = tkFileDialog.askopenfilename(initialdir = pathtoflight,title = "There are a few {} files for {} block = {}, select which you want to use".format(parametr,fid,block),filetypes = (("{} files".format(typef),"*{0}*{1}*.{2}".format(str(fid),parametr,typef)),("all files","*.{}".format(typef))))
            layer = root.filename
            root.destroy()
        else:
            layer =  layer[0]
            
        return layer
    
    
    def identical_miss_planted(self, planted,missshp):
        """
        Check beetwen planted and missing shp file identical point
        ----------
        planted : str
           Path to shp file with planted points
          
        missshp : str
           Path to shp file with missing points
           
        Returns
        -------
        delete identical points in shp file 
        
        """
        
        out_table = os.path.join(logfolder,"new_tab{}.txt".format(random.randint(0,999)))
        tab = arcpy.PointDistance_analysis (planted, missshp, out_table, "0.2 Meters")
        if int(str(arcpy.GetCount_management(tab))) > 0:
            cursorlayer = arcpy.da.SearchCursor(tab,'INPUT_FID')
            fid = list(set(row[0] for row in cursorlayer))
            arcpy.Delete_management(out_table)
            message = 'There are identical points in miss and planted, in {} in FID {}'.format(os.path.basename(planted),fid)
            self.create_log(message, True)
            ask = tk.messagebox.askquestion ('Do you want to stop script?',message,icon = 'warning')
            if ask == "yes":
                raise ValueError(message)
                
        return False
    
    
    def checkField(self,shppath,atname):
        """
        проверка есть ли такое поле в шейп файлах
        -----------------------------
        shppath: str
           Path to shp file wich you want to check
        atname - имя атрибута для проверки
        -----------------------------
        return true если поле есть в шейп файле и false если нету
        """
        field_names = [f.name for f in arcpy.ListFields(shppath)]
        if atname not in field_names:
            message = 'There are no {} attribute in {} file'.format(atname,shppath)
            self.create_log(message)
            return False
        else:
            return True
    
    
    def checkEmptyValue(self,inFc,field):
        """
        
        проверка есть ли пустые значения в атрибуте
        -----------------------------
        inFc: str
           Path to shp file wich you want to check
        shppath: str
           Path to shp file wich you want to check
          
        -----------------------------
        return true если поле есть в шейп файле и false если нету
        """
        values = [r[0] for r in arcpy.da.SearchCursor (inFc, field) if r[0] == " " or r[0] == 0]
        if len(values) >=1:
            ask = tk.messagebox.askquestion ('There are {} empty values in {} shp {} attribute'.format(len(values),os.path.basename(inFc),field),'Do you want to stop script?',icon = 'warning')
            if ask == "yes":
                message = "There are {} empty values in {} shp {} attribute".format(len(values),inFc,field)
                self.create_log(message)
                raise ValueError(message)
        return True
    
    
    def checkAnd_fill(self,inFc,field):
        """
        Проверяет на пустые строки атрибут, работает для атрибутов с одинаковыми значениеями, если находит пустое предлагает заменить
        
        """
        curs = arcpy.da.SearchCursor(inFc,field)
        values = [r[0] for r in curs if r[0] == " " or r[0] == 0]
        del curs
        curs = arcpy.da.SearchCursor(inFc,field)
        unvalue = list(set(row[0] for row in curs if row[0] != " " ))
        if len(values) >=1:
            ask = tk.messagebox.askquestion ('Do you want set  {}  for all attributes?'.format(str(unvalue)),'There are {} empty values in {} shp {} attribute'.format(len(values),os.path.basename(inFc),field),icon = 'warning')
            if ask == "yes":
                #expression = 'class = {}'.format(unvalue[0])
                arcpy.CalculateField_management(inFc,field,unvalue[0], "PYTHON")
                message = 'Filled {} empty values in {} shp {} attribute'.format(len(values),os.path.basename(inFc),field)
                self.create_log(message)
        return unvalue[0]
    
    
    
    
    
    def checkEmptyValue_missID(self,missshp,field):
        """
        
        проверка есть ли пустые значения в атрибуте
        -----------------------------
        inFc: str
           Path to shp file wich you want to check
        shppath: str
           Path to shp file wich you want to check
          
        -----------------------------
        return true если поле есть в шейп файле и false если нету
        """
        print (field)
        values = [r[0] for r in arcpy.da.SearchCursor (missshp, field) if r[0] == '' or r[0] == 0 or r[0] == " "]
        print (values)
        if len(values) >=1:
            ask = tk.messagebox.askquestion ('Do you want to fill it ?','There are {} empty values in {} shp {} attribute'.format(len(values),os.path.basename(missshp),field),icon = 'warning')
            if ask == "yes":
                curs = arcpy.da.UpdateCursor(missshp, field)
                value = 0
                for row in curs:
                    value+=1
                    row[0] = value
                    curs.updateRow (row)
        return True
    
    
    
    
    
    def get_geometry_to_csv(self,missshp):
        
        """
        save csv with x and y coordinats,works for points
        missshp - шейп файл с пропущенными деревьями для которого нужно сделать csv
        ---------------------------------------
        return csv file
        """
        name = os.path.basename(missshp)[:-4]
        csvfolder = os.path.join(os.path.dirname(os.path.dirname(missshp)),'csv')
        if not os.path.exists(csvfolder):os.makedirs(csvfolder)
        field_names = [f.name for f in arcpy.ListFields(missshp)]
        trees = [i for i in field_names if 'treeid' == i.lower() ][0]
        if trees not in field_names:
            #ask = pythonaddins.MessageBox('Do you want to add and calculate it?', 'There is no tree ID attribute for {} shapefile'.format(name), 1)
            ask = tk.messagebox.askquestion ('There is no tree ID attribute for {} shp'.format(name),'Do you want to add and calculate treeId field?',icon = 'warning')
            if ask == "yes":
                arcpy.AddField_management (missshp, trees, "TEXT",field_length = 8)
                self.checkEmptyValue_missID(missshp, trees)
            else:
                return
        self.checkEmptyValue_missID(missshp, trees)
        path = os.path.join(csvfolder,name +'_X_Y.csv')
        fieldnames = [trees, 'Point_X', 'Point_Y']# fields to add as titel in csv
        with open(path, "wb") as out_file:# for 2 python need use wb to avoid empty lines
            writer = csv.DictWriter(out_file, delimiter=';', fieldnames=fieldnames,dialect='excel')
            curs = arcpy.da.SearchCursor(missshp,[trees,"SHAPE@X","SHAPE@Y"])
            writer.writeheader()
            for row in curs:
                writer.writerow({fieldnames[0]:int(row[0]),fieldnames[1]:float(row[1]),fieldnames[2]:float(row[2])}) 
                
        message = "Have created csv file for {}".format(name)
        self.create_log(message)
        return      
        
    
    
    def check_shp_file (self, listCheckShp):
        
        namemisstress = None
        global logfolder
        # get path to folder with shp to create log file with report
        logfolder = os.path.dirname(listCheckShp[0])
        
        for shp in listCheckShp:
            
            fid = self.get_fid_from_filename(os.path.basename(shp)[:-4])
            
            self.check_identcal(shp)
            
            # для поиска миссинг трисс и использование его для проверки наложение точек
            if namemisstress == None:
                treesmiss = self.find_layer(os.path.dirname(shp), fid, parametr = 'missing',typef = 'shp')
                if len(treesmiss) > 1:
                    # проверка наложения миссингов
                    self.check_identcal(treesmiss)
                    self.identical_miss_planted(shp,treesmiss)
                    # создание csv и заполнение колоночки три ид
                    self.checkAnd_fill(treesmiss,'class')
                    self.get_geometry_to_csv(treesmiss)
                    # заполнить имя что бы не повторять в цикле
                    namemisstress = os.path.basename(treesmiss)
                    if self.checkField(treesmiss,'variety') and self.checkField(treesmiss,'class') :
                        curs = arcpy.da.SearchCursor(treesmiss,'class')
                        querylist = list(row[0] for row in curs)
                        for cl in querylist:
                            querycl = '"{}" ='.format('class') + "'" + cl + "'"
                            self.get_count_log(treesmiss,query = querycl)
                            
                    elif self.checkField(treesmiss,'variety'):
                        
                        self.get_count_log(treesmiss)
                    else:
                        self.get_count_log(treesmiss,'class')
                
                
            if self.checkField(shp,'class'):
                self.checkAnd_fill(shp,'class')
                
            
            if self.checkField(shp,'variety'):
                self.checkEmptyValue(shp,'variety')
                self.get_count_log(shp)
            else:
                self.get_total_points(shp, log=True) 
        
        
            
            
            
        




