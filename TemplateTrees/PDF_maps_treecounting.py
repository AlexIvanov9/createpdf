# -*- coding: utf-8 -*-
import arcpy
from arcpy.sa import *
import datetime
import os,glob,shutil
#import logging
import re,csv
import pythonaddins
#from Tkinter import *
import tkFileDialog
import tkinter as tk
from tkinter import messagebox
import random
from  check_shp import CheckShpFile


# выбираем ид касса если хотим перезапустить отдельный, если 0 обрабатываем все классы 
field = 0#['4','5','8','20','21','23','24','27','36','67','68','69']

#нужно брать только одну ферму для более корректной работы 
farm = ["56198"]#['54493']

# True делать пдф, False не делать
plantedpdf = True
misspdf = False

# mxd которое будем для пдф когда отображаем все растения
mxdplanted = 'Without_varieties_planted.mxd'
mxdmissing = 'Without_varieties_indexed.mxd'

# если нужно создать csv сохранит в структуре полета создаст папку csv и проверить шейп файлы на пустные значение 
#проверить на совпадение
previewCheckSHP = False

# по умолчанию бьет на блоки используя field boundary и значения с name атрибута, если False то использует шейп с точками и классы
# желательно создавать тестовое поле для дележки на атрибуты
byblock = True
splitat = 'name'

clipbypolygon = True
farmsname = {56198:"Crabtree 2",56225:"Omsum",55494:"Mulkeys",55472:'Kerarbury',47711:'Kern Martin',47361:'Mariani Almonds',49287:'Cuzner Almonds',53908:'Cadell',54493:'Claravale'}



"""
# need run in spyder to get farmsname for client

def get_list_farms_id(client_id):
    
   ft = improc.dbops.dbio.get_table("Fields")
   fe = ft.loc[ft['Cust_ID']==client_id]
   try:
       ids = list(fe.index)
       return ids
   except IndexError:
       print("Faild")


ids = get_list_farms_id(client_id)

# get all filenames as dictinary
farmsname = {}

def get_field_name_from_id(field_id):
   ft = improc.dbops.dbio.get_table("Fields")
   fe = ft.loc[ft.index==field_id]
   try:
       fname = str(fe['Field_Name'].values[0]).replace(':','')
       if fname[-1] == ' ':
           fname = fname[:-1]
       farmsname.update({field_id : fname})
       return fname
   except IndexError:
       print("Faild")

for name in ids:
    get_field_name_from_id(name)
"""




class MapToPDF():
    
    def __init__(self):
        arcpy.env.overwriteOutput = True
    
    
    
    def get_fid_from_filename(self,filename):
        """
        для нахождение фид из имени файла
        """
    
        fid_regex = re.compile("\d\d\d\d-[\d]{1,2}-[\d]{1,2} (?P<fid>[\d]+) ")
        farm_ids = fid_regex.findall(filename)
    
        if farm_ids:
            farm_id = int(farm_ids[0])
            return farm_id
        else:
            raise ValueError("Could not determine farm id.")
            
    def checkField(self,shppath,atname):
        """
        проверка есть ли такое поле в шейп файлах
        """
        field_names = [f.name for f in arcpy.ListFields(shppath)]
        if atname not in field_names:
            print ('There are no {} attribute in {} file'.format(atname,shppath))
            return False
        else:
            return True
    
    def create_query(self,treesmiss,selection):
        """
        создает запрос для мисс трисс если там есть класс
        """
        arcpy.MakeFeatureLayer_management(treesmiss,'Treemiss')
        selectmisstrees = arcpy.SelectLayerByLocation_management('Treemiss', 'intersect', selection)# to use only missing trees for 
        curstr = arcpy.da.SearchCursor(selectmisstrees,'class')
        queryMissTr = list(set(row[0] for row in curstr))
        try:
            q = ''
            if len(queryMissTr) > 1:
                q = []
                for i in queryMissTr[1::]:
                    text = ' Or "class" = ' + "'" + str (i[0]) + "'"
                    classname = str (i[0])
                    q.append(text)
                    q = ' '.join(map(str, q))
                
            query = '"class" = ' + "'" + str(queryMissTr[0])+"'{}".format(q)
            return query
                
        except Exception as e:
            query = '"class" = ' + "'" + str(999)+"'"
            print('There are no miss trees for this class')# нужно сохранять в лог файл
            return query
    
    def query_for_border(self,selection,field):
        """
        создает запрос для границы поля
        """
        curs = arcpy.da.SearchCursor(selection,field)
        querybor = [i[0] for i in curs]
        q = ''# emty query if we use only one polygon
        if len(querybor) > 1:
            q = []
            for i in querybor[1::]:
                text = ' Or {0} = {1}'.format(field,i)
                q.append(text)
            q = ' '.join(map(str, q))
            #querybor = '"FID" = ' + "'"+str(querybor)+"'"
        querybor = '{0} = {1}{2}'.format(field,querybor[0],q)
        return querybor
        
    
    def save_mxd (self,savemxd,name,mxd,typeplanted = True):
        """
        функция для сохранения mxd файлов
        """
        tfolder = os.path.join(savemxd,'MXDs')
        if not os.path.exists(tfolder):
            os.makedirs(tfolder)
        if typeplanted:    
            pathmxd = os.path.join(tfolder,name + '.mxd')
        else:
            pathmxd = os.path.join(tfolder,name + ' indexed' + '.mxd')
        mxd.saveACopy(pathmxd,'10.3')
        del mxd
        return
    
    
    def variety_changes (self,layer,layermiss,mxdtemplate):
        """
        используется для создания пдф файлов в которых есть сорта
        """
        
        cursorlayer = arcpy.da.SearchCursor(layer,'variety')
        layer.symbology.addAllValues()
        if layermiss != " ":
            layermiss.symbology.addAllValues()
        #if mxdtemplate != mxdmissing:
            #arcpy.ApplySymbologyFromLayer_management(layer,layermiss)
        if len(list(set(row[0] for row in cursorlayer))) > 1:
            lnumber = arcpy.GetCount_management(layermiss)
            if len(lnumber) == 4:
                lnumber = lnumber[:1] +',' + lnumber[1::]
            layermiss.name = 'Missing \n ({})'.format(lnumber)
            number = str(arcpy.GetCount_management(layer))
            if len(number) == 4:
                number = number[:1] +',' + number[1::]
            elif len(number) == 5:
                number = number[:2] +',' + number[2::]
            layer.name = 'Planted \n ({})'.format(number)
        
    
    def find_layer(self,pathtoflight, folder , fid = '', parametr = '',typef = 'shp',block = ''):
        """
        Parameters:
            folder takes the name of the folder in flight (tree count, registered)
            parameter take the name of an object (VNIR for tif, miss for missing trees)
            typef taking the type of file (tif, shp)
        Return:
            path to file
        """
        layer = glob.glob(os.path.join(pathtoflight, folder ,"*{0}**{1}*.{2}").format(str(fid), parametr, typef))
        if len(layer) == 0:
            print ('For fid {0} there is no file {1} in {2} folder '.format(str(fid), typef, folder))
            layer = ''
            return  layer
            
        if len(layer) > 1:
            root = tk.Tk()
            tp = os.path.join(pathtofligt,folder)
            root.filename = tkFileDialog.askopenfilename(initialdir = tp,title = "There are a few {} files for {} block = {}, select which you want to use".format(parametr,fid,block),filetypes = (("{} files".format(typef),"*{0}*{1}*.{2}".format(str(fid),parametr,typef)),("all files","*.{}".format(typef))))
            layer = root.filename
            root.destroy()
        else:
            layer =  layer[0]
            
        return layer
    
    
    def get_mxd(self,mxdname):
        
        """ взятие переменных проекта
        """
        mxd = arcpy.mapping.MapDocument(mxdname)
        layer = arcpy.mapping.ListLayers(mxd,'Planted')[0]
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        layermiss = arcpy.mapping.ListLayers(mxd,'Missing')[0]
        borders = arcpy.mapping.ListLayers(mxd,'borders')[0]
        background = arcpy.mapping.ListLayers(mxd,'background')[0]
        
        #nameplant = arcpy.mapping.ListLayers(mxd,' ')[0]
        
        return mxd,layer,df,layermiss,borders,background
    
    def clip_raster(self,image,outfolder, geometry,imname):
        """
        
        """

        outpath = os.path.join(outfolder, "{}.tif".format(imname))
        if mxdmissing == mxdmissing and os.path.exists(outpath):
            return image
        outExtractByMask = ExtractByMask(image,geometry)
        outpath = os.path.join(outfolder, "{}.tif".format(imname))
        outExtractByMask.save(outpath)
        return outpath
        

            
    def exportMap(self, shp, pathExport, mxdtemplate, typeplanted = True):
        """
        shp - лист с указание пути на папку и названием файла, что бы заменить в скрипте
        pathExport - путь на папку для экспорта пдф файлов
        mxdtemplate - шаблон mxd который будем применять
        typeplanted - переменная для названия файлов если True то для растений если False то для потерянных деревьев
        """
        
        shppath = shp[0] + '//' + shp[1] + '.shp'
        namepdf = farmsname[int(fid)]
        mxd,layer,df,layermiss,borders,background  = self.get_mxd(mxdtemplate)# вызов переменных
        
        
        layer.replaceDataSource(shp[0],'SHAPEFILE_WORKSPACE',shp[1])# замена шейп файла в мксд
        #nameplant.replaceDataSource(shp[0],'SHAPEFILE_WORKSPACE',shp[1])# замена шейп файла в мксд
        
        # проверка есть ли класс, с этого момента нужно изменять под мозайку или полигоны
        if self.checkField(shppath,'class'):
            cursorlayer = arcpy.da.SearchCursor(layer,'class')
            clname = list(set(row[0] for row in cursorlayer))
            namepdf = farmsname[int(fid)] + ' ' + str(clname[0])
            if field > 0:
                if str(clname[0]) != str(field):
                       return
        # image block
        imagepath = self.find_layer(pathtofligt, 'registered merged', fid , parametr = 'VNIR',typef = 'tif')
        background.replaceDataSource(os.path.dirname(imagepath),'RASTER_WORKSPACE',os.path.basename(imagepath)[:-4])
        
        # border block
        border = glob.glob(os.path.join(pathtofligt,"field borders","*{}*.shp").format(str(fid)))[0]# get shp with borders for field
        borders.replaceDataSource(os.path.dirname(border),'SHAPEFILE_WORKSPACE',os.path.basename(border)[:-4])
        
        # make layers for selection
        arcpy.MakeFeatureLayer_management(border,'Borders')
        arcpy.MakeFeatureLayer_management(shppath,'Planted')
        selection = arcpy.SelectLayerByLocation_management('Borders', 'intersect', 'Planted')# to choose polygon which we need for map using shp with plant points

        print (self.query_for_border(selection,"FID"))
        borders.definitionQuery = self.query_for_border(selection,"FID")
        #borders.definitionQuery = querybor
        
        # block for missing trees file
        treesmiss = self.find_layer(pathtofligt,'tree count', fid, parametr = 'missing',typef = 'shp')
        if len(treesmiss) > 1: # проверяем есть ли в наличии путь для миссинг трисс для дальнейшей обработки
            layermiss.replaceDataSource(os.path.dirname(treesmiss),'SHAPEFILE_WORKSPACE',os.path.basename(treesmiss)[:-4])
            if self.checkField(treesmiss,'class'):
                layermiss.definitionQuery = self.create_query(treesmiss,selection)    
        else:
            print ('File for miss trees is empty')
        
        df.extent = borders.getSelectedExtent(True) # get extend borders polygon
        df.scale = df.scale * 1.07
        
        
        
        if self.checkField(layer,'variety'):
            # проблема с добавлением слоев при добавлении слоя в индекс картах появляется первый цветной слой, плюс отличается цвет , нужно как-то исправить
            self.variety_changes(layer,layermiss,mxdtemplate)# будет ломаться если миссинг трисс отсутсвует
        
        elemList = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")# получение листа всех элементов лейаута
        
        
        #namepdf = farmsname[int(fid)] + ' ' + str(clname[0]) # пересмотреть и может вести переменную для имени на сдучай когда нет класса

        for elem in elemList:
            if elem.name == "NewName":
                    try:
                        if len(namepdf) > 20:
                            elem.text =  "<FNT size = '17'>" + str(namepdf)  +  "</FNT>"
                            continue 
                        namepdf = namepdf.replace('_',' ')
                        elem.text = namepdf
                    except:
                        elem.text = str(fid)
                        continue
        
        
            #except Exception as e::
                #print(e)
                #elem.text = str(fid)     
        if typeplanted:  
            arcpy.mapping.ExportToPDF(mxd, pathExport + '//' + namepdf + '.pdf',"PAGE_LAYOUT")
        else:
            arcpy.mapping.ExportToPDF(mxd, pathExport + '//' + namepdf + ' indexed' + '.pdf',"PAGE_LAYOUT")
        
        self.save_mxd (shp[0],namepdf,mxd,typeplanted)
        
        return



    def exportMapbyBoundary(self, shp, pathExport, mxdtemplate, typeplanted = True, splitat = splitat):
                
        shppath = shp[0] + '//' + shp[1] + '.shp'
            
        mxd,layer,df,layermiss,borders,background  = self.get_mxd(mxdtemplate)# вызов переменных
            
        border = self.find_layer(pathtofligt, 'field borders', fid , parametr = '',typef = 'shp')
            
            #border = glob.glob(os.path.join(pathtofligt,"field borders","*{}*.shp").format(str(fid)))[0]
        # make layers for selection
        arcpy.MakeFeatureLayer_management(border,'Borders')
        arcpy.MakeFeatureLayer_management(shppath,'Planted')
        selection = arcpy.SelectLayerByLocation_management('Borders', 'intersect', 'Planted')# to choose polygon which we need for map using shp with plant points

        print (self.query_for_border(selection,"FID"))
        borders.replaceDataSource(os.path.dirname(border),'SHAPEFILE_WORKSPACE',os.path.basename(border)[:-4])
        borders.definitionQuery = self.query_for_border(selection,"FID")
            
        #borders.replaceDataSource(os.path.dirname(border),'SHAPEFILE_WORKSPACE',os.path.basename(border)[:-4])
        #curborder = arcpy.da.SearchCursor(border,splitat)
        curborder = arcpy.da.SearchCursor(borders,splitat)
        queryBorder = list(row[0] for row in curborder)
        print (queryBorder)
        for letter in  queryBorder:
            #print (letter)
            try:
                if int(letter) == 0:
                    continue
            except:
                pass
            query = '"{}" ='.format(splitat) + "'" + letter + "'"
            
            borders.definitionQuery = query
            # на случай если в значении комбинация из пару цифр класс + номер
            df.extent = borders.getSelectedExtent(True) # get extend borders polygon
            df.scale = df.scale * 1.15
            tempfolder = os.path.join(shp[0],'tempfolder')
            if not os.path.exists(tempfolder):os.makedirs(tempfolder)
            
            pname = 'plant{}.shp'.format(letter)
            
            planted = arcpy.Clip_analysis(shppath,borders,os.path.join(tempfolder,pname))
            
            layer.replaceDataSource(tempfolder,'SHAPEFILE_WORKSPACE',pname[:-4])# замена шейп файла в мксд
                
            try:    
                treesmiss = self.find_layer(pathtofligt,'tree count', fid, parametr = 'missing',typef = 'shp')
                mname = 'Miss{}.shp'.format(letter)
                miss = arcpy.Clip_analysis(treesmiss,borders,os.path.join(tempfolder,mname))
                layermiss.replaceDataSource(tempfolder,'SHAPEFILE_WORKSPACE',mname[:-4])
            except:
                layermiss = " "
            imagepath =  self.find_layer(pathtofligt, 'registered merged', fid , parametr = 'VNIR',typef = 'tif')
            
            if clipbypolygon:
                imname = 'image{}'.format(letter)
                imagepath = self.clip_raster(imagepath,tempfolder ,borders, imname)  
                background.replaceDataSource(tempfolder,'RASTER_WORKSPACE',imname)
            else:
                background.replaceDataSource(os.path.dirname(imagepath),'RASTER_WORKSPACE',os.path.basename(imagepath)[:-4])
            
            
            if self.checkField(planted,'variety'):
                
                self.variety_changes(layer,layermiss,mxdtemplate)# будет ломаться если миссинг трисс отсутсвует
        
            elemList = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")# получение листа всех элементов лейаута
                # проверка есть ли класс, с этого момента нужно изменять под мозайку или полигоны
                
            namepdf  = ''    
            if self.checkField(shppath,'class'):
                cursorlayer = arcpy.da.SearchCursor(layer,'class')
                #self.checkEmptyValue(shppath,'class')
                clname = list(set(row[0] for row in cursorlayer))
                print (clname)
                namepdf = farmsname[int(fid)] + ' ' + str(clname[0])
                
                if field > 0:
                    if str(clname[0]) != str(field):
                        return
                """
                if field > 0:
                    if str(clname[0]) not in field:
                        return
                if field > 0:
                    if str(clname[0]) != str(field):
                        return
                if field > 0:
                    if int(clname[0]) < field:
                        return
                """
            # пересмотреть блок
            if len(namepdf) > 1 and letter != '':namepdf = namepdf + '-' + str(letter)
            elif len(namepdf) > 1 and letter == '': namepdf
            else:namepdf = farmsname[int(fid)] + '-' + str(letter)# пересмотреть и может вести переменную для имени на сдучай когда нет класса
                

            for elem in elemList:                    
                if elem.name == "NewName":
                    try:
                        if len(namepdf) > 15:
                            elem.text =  "<FNT size = '17'>" + str(namepdf)  +  "</FNT>"
                            continue 
                        namepdf = namepdf.replace('_',' ')
                        elem.text = namepdf
                    except:
                        elem.text = str(fid)
                        continue
        
        
            #except Exception as e::
                #print(e)
                #elem.text = str(fid)     
            if typeplanted:  
                arcpy.mapping.ExportToPDF(mxd, pathExport + '//' + namepdf + '.pdf',"PAGE_LAYOUT")
            else:
                arcpy.mapping.ExportToPDF(mxd, pathExport + '//' + namepdf + ' indexed' + '.pdf',"PAGE_LAYOUT")
        
            self.save_mxd (shp[0],namepdf,mxd,typeplanted)
        
        return





    def getmapbook(self, mypath, pathexport):
        """
        компоновка пдф файлов в один
        """
        pdfdoc = arcpy.mapping.PDFDocumentCreate(pathexport)
        for (dirpath, dirnames, filenames) in os.walk(mypath):
            pdfmaps = [x for x in os.listdir(dirpath) if x.endswith(".pdf")]
            for pdf in pdfmaps:
                pdf = dirpath + '//' + pdf
                pdfdoc.appendPages(pdf)
        pdfdoc.saveAndClose()
        shutil.rmtree(mypath)
        return pdfdoc

    
    def splite_path(self,path):
        """
        Берет путь к папке с полетом и отбирает нужные шейпы
        Parameters
        ----------
        shp : str
           Path to folder with flight
           
        Returns
        -------
        delete identical points in shp file 
        
        """
        
        shpPath = []
        shpPath.append(os.path.dirname(path))
        shpPath.append(os.path.basename(path)[:-4])
        return shpPath
    
    
    def checkListShp(self,pathtoflight):
        """
        Берет путь к папке с полетом и отбирает нужные шейпы
        Parameters
        ----------
        shp : str
           Path to folder with flight
           
        Returns
        -------
        лист с нужными шейп файлами для работы скрипта 
        
        """
        selectlist = []
        passlist = ['shp_vqt','shp vqt','missing_trees','missing']
        shpfiles = glob.iglob(os.path.join(pathtoflight,"tree count\*.shp"))
        for shp in shpfiles:
            if len([i for i in passlist if i in os.path.basename(shp)[:-4].lower()]) >= 1:
                continue
            fid = self.get_fid_from_filename(os.path.basename(shp)[:-4])
            if len(farm) >= 1 and  str(fid) not in farm:
                continue
            selectlist.append(shp)
        
        return selectlist
            
            

    def getPdf (self, pathTofolder, pathExport, mapbook = False):
        
        if mapbook == True:
            mapbookpath = pathExport # заменить путь для конечного экспорта
            pathExport = os.environ["TMP"] + "\\Maps"# новый путь для экспорта одиночных пдф
            if not os.path.exists(pathExport):
                os.makedirs(pathExport)
        
        # list ends of images that we shouldt use
        shpfiles = self.checkListShp(pathTofolder)
        if previewCheckSHP:
            CheckShpFile().check_shp_file (shpfiles)
        
        for shp in shpfiles:
            # для передачи по всему классу
            global fid
            fid = self.get_fid_from_filename(os.path.basename(shp)[:-4])
            shpPath = self.splite_path(shp)
            #print (shp)
            #try:
            #self.exportMap(shpPath, pathExport)
            if plantedpdf:
                print(shpPath)
                if byblock:self.exportMapbyBoundary(shpPath, pathExport,mxdtemplate = mxdplanted)
                if byblock == False:self.exportMap(shpPath, pathExport,mxdtemplate = mxdplanted)
                    
            if misspdf:
                if byblock:self.exportMapbyBoundary(shpPath, pathExport,mxdtemplate = mxdmissing,typeplanted = False)
                if byblock == False:self.exportMap(shpPath, pathExport,mxdtemplate = mxdmissing,typeplanted = False)
                
            
            #except Exception as e:
                #print (e)
                #print (shpPath)
                    
        if  mapbook == True:
            name = str(datetime.datetime.now())[0:13].replace('-', '')# создать имя для одного цельного пдф файла
            mapbookpath = mapbookpath + "\\" + name + ".pdf"
            self.getmapbook(pathExport, mapbookpath)

print ('Please insert path to the flight folder')

pathtofligt = raw_input()  
#pathtofligt = r'D:\Google drive Ceres\Freelancers\Projects\Special Projects - Production\Tree Count\Flight 8471'          

print ('Please insert path to the output folder')

pathoutput = raw_input()  

#an example
pdf = MapToPDF()
#listshp = []# лист имен шейп файлов которые обрабатывать
#pdf.getPdf( pathtofligt,listshp, pathoutput , mapbook = False, csv = csv )
pdf.getPdf( pathtofligt, pathoutput , mapbook = False)





