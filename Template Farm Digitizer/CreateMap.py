# -*- coding: utf-8 -*-
import arcpy
import datetime
import shutil
import os
import logging
import glob

class MapToPDF():
    
    def get_log(self,nameapp, message ):
        """
        создание лог файлов на рабочем столе
        """
        tfolaer = os.path.join('C:\\', 'Users', 'User', 'Desktop','Atributes')
        if not os.path.exists(tfolaer):
            os.makedirs(tfolaer)
        now = datetime.datetime.now()
        name = now.strftime("%Y-%m-%d")
        logfile = os.path.join(tfolaer,str(name) + '.log')
        logger = logging.getLogger(nameapp)
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(logfile)
        formatter = logging.Formatter("%(name)s | %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.info(message)
        return
    
    def get_mxd(self,mxdname):
        """ взятие переменных проекта
        """
        mxd = arcpy.mapping.MapDocument(mxdname)
        layer = arcpy.mapping.ListLayers(mxd,'InsertShp')[0]
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        return mxd,layer,df

    def dissolv(self,inputshp,fields):
        shpPath = []
        tfolaer = os.path.join(inputshp[0],'Dissolve')
        if not os.path.exists(tfolaer):
            os.makedirs(tfolaer)
        pathshp = os.path.join(inputshp[0],inputshp[1] + '.shp')
        output_fc = os.path.join(tfolaer,str(inputshp[1]) + '.shp')
        shp = arcpy.Dissolve_management(pathshp,output_fc,fields)
        shpPath.append(os.path.dirname(output_fc))
        shpPath.append(os.path.basename(output_fc)[:-4])
        
        return shpPath

    def saveMXD(self,path,name):
        tfolaer = os.path.join(inputshp[0],'MXDs')
        if not os.path.exists(tfolaer):
            os.makedirs(tfolaer)
        
        return


            
    def exportMap(self, shp, pathExport,dissolv = True,mxds = True):
        """
        """
        savemaxd = shp[0]# путь в папку для сохранение мксд, можем сменится иза создания дисолв
        mxd,layer,df = self.get_mxd('Tulare 43_row_space.mxd')# вызов переменных
        if dissolv:# change shp to shp with dissold
            shp = self.dissolv(shp,["Descriptio","Acres","name","row_space"])
        layer.replaceDataSource(shp[0],'SHAPEFILE_WORKSPACE',shp[1])# замена шейп файла в мксд
        df.extent = layer.getSelectedExtent(True)
        df.scale = df.scale * 1.07
        elemList = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")# полечение листа всех элементов лейаута
        for elem in elemList:
                if elem.name == "NewName":
                    if len(str(shp[1])) > 25:
                        elem.text =  "<FNT size = '11'>" + str(shp[1])  +  "</FNT>"
                        continue
                    if len(str(shp[1])) > 12:
                        elem.text = "<FNT size = '15'>" + str(shp[1]) + "</FNT>"
                        continue
                    else :
                        elem.text = shp[1]
                        continue
                elif elem.name == "Acres":
                    try:
                        acr = self.get_acr(shp)
                    except Exception as e:
                        print (e)
                        acr = [0,0]
                    elem.text = 'Gross acres: ' + str(acr[1]) + ' / ' + 'Net acres: ' + str(acr[0])
                    #elem.text = 'Net acres: ' + str(acr)
        #arcpy.RefreshActiveView()
        arcpy.mapping.ExportToPDF(mxd, pathExport + '//' + shp[1] + '.pdf',"PAGE_LAYOUT")
        if mxds:
           tfolaer = os.path.join(savemaxd,'MXDs')
           if not os.path.exists(tfolaer):
               os.makedirs(tfolaer)
           pathmxd = os.path.join(tfolaer,shp[1] + '.mxd')
           mxd.saveACopy(pathmxd,'10.3')
        del mxd
        return

    def checkAt(self,shp):
        """
        проверка атрибутов на правильность написание
        """
        fieldcheck = ['gross acres', 'net acres', 'roadway', 'well site', 'reservoir', 'solar site',
                      'fallow and recharge ground', 'built up area', 'canal']
        shppath = shp[0] + '//' + shp[1] + '.shp'
        print (shppath)
        field_names = [f.name for f in arcpy.ListFields(shppath)]
        if "descriptio" in field_names or "descriptio" in field_names:
            curs = arcpy.da.UpdateCursor(shppath, ['descriptio','FID'])
            for i in curs:
                if i[0] not in fieldcheck:
                    nameid = 'Shp name is {}, value id {}'.format(str(shp[1]),str(i[1]))
                    self.get_log(nameid,i[0])
                    #print shp  # get path to problem shp
                    #print i[0]  # get problem value
        return
    
    def chechField(self,shp):
        """
        проверка есть ли такое поле в шейп файлах
        """
        shppath = shp[0] + '//' + shp[1] + '.shp'
        print (shppath)
        field_names = [f.name for f in arcpy.ListFields(shppath)]
        #if "descriptio" in field_names or "descriptio" in field_names:
        if "row_space" not in field_names:
            nameid = 'Shp name is {}, there is no atr'.format(str(shp[1]))
            arcpy.AddField_management (shppath, "row_space", "TEXT")
            self.get_log(nameid,'')
            
            """
            curs = arcpy.da.UpdateCursor(shppath, ['descriptio','FID'])
            for i in curs:
                if i[0] not in fieldcheck:
                    nameid = 'Shp name is {}, value id {}'.format(str(shp[1]),str(i[1]))
                    self.get_log(nameid,i[0])
                    #print shp  # get path to problem shp
                    #print i[0]  # get problem value
            """
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

    # def get_acr (self, path):
    #     exel = path[0] + '//' + path[1] + '.xlsx'
    #     value = pd.read_excel(exel)
    #     gross = value[value['category'] == 'gross acres']
    #     gross = round(float(gross['Acres']), 2)
    #     net = value[value['category'] == 'net acres']
    #     net = round(float(net['Acres']), 2)
    #     return gross, net

    def get_acr (self, path):
        shp = path[0] + '//' + path[1] + '.shp'
        curs = arcpy.da.SearchCursor(shp, ['descriptio', 'Acres'])
        acres = 0
        total = 0
        for i in curs:
            if i[1] == ' ':
                continue
            if i[0] == 'net acres':
                acres += float(i[1])
                total += float(i[1])
                continue
            total += float(i[1])
        acres = round(acres, 2)
        total = round(total, 2)
        return acres,total

    def getPdf (self, pathTofolder, listshp, pathExport, mapbook = False):
        if mapbook == True:
            mapbookpath = pathExport
            pathExport = os.environ["TMP"] + "\\Maps"
            if not os.path.exists(pathExport):
                os.makedirs(pathExport)
        #shpfiles = glob.glob(r"D:\Google drive\Freelancers\Projects\Special Projects - Production\Farm Digitization\**\digitized\*.shp")
        shpfiles = glob.glob(r"D:\Google drive\Freelancers\Projects\Special Projects - Production\Farm Digitization\Done\*.shp")
        for shp in shpfiles:
            shpPath = []
            shpPath.append(os.path.dirname(shp))
            shpPath.append(os.path.basename(shp)[:-4])
            try:
                self.checkAt(shpPath)
                self.exportMap(shpPath, pathExport)
            except Exception as e:
                print (e)
                    
        if  mapbook == True:
            name = str(datetime.datetime.now())[0:13].replace('-', '')
            mapbookpath = mapbookpath + "\\" + name + ".pdf"
            print mapbookpath
            self.getmapbook(pathExport, mapbookpath)

#an example
pdf = MapToPDF()
listshp = []# лист имен шейп файлов которые обрабатывать
pdf.getPdf( r'D:\Google drive\Freelancers\Projects\Special Projects - Production\Farm Digitization',listshp, r'D:\Fiardo\PDFs', mapbook = True)


#D:\Sasha\Goodle_drive\Freelancers\Projects\FM Vegetation boundaries\FM_updateMerge
#D:\Sasha\Goodle_drive\Freelancers\Projects\FM Vegetation boundaries\FM_updated






