# -*- coding: utf-8 -*-
import arcpy
import datetime
import shutil
import os
import logging
import glob
import re
import csv

class MapToPDF():
    
    
    
    
    def get_fid_from_filename(self,filename):
    
        fid_regex = re.compile("\d\d\d\d-[\d]{1,2}-[\d]{1,2} (?P<fid>[\d]+) ")
        farm_ids = fid_regex.findall(filename)
    
        if farm_ids:
            farm_id = int(farm_ids[0])
            return farm_id
        else:
            raise ValueError("Could not determine farm id.")
            
            
            
            
            
    def get_geometry_co_csv(self,pathshp):
        """
        save csv with x and y coordinats near shp
        """
        fieldnames = ['TreeId', 'Point_X', 'Point_Y']
        
        
        field_names = [f.name for f in arcpy.ListFields(pathshp)]
        
        if "treeid" not in field_names:
            return "There is no treeid field"
            
        name = os.path.basename(pathshp)[:-4]
        dirpath = os.path.dirname(pathshp)
        path = os.path.join(dirpath,name[:-4]+'_X_Y.csv')
        with open(path, "wb") as out_file:# for 2 python need use wb to avoid empty lines
            writer = csv.DictWriter(out_file, delimiter=';', fieldnames=fieldnames,dialect='excel')
            curs = arcpy.da.SearchCursor(pathshp,["treeid","SHAPE@X","SHAPE@Y"])
            writer.writeheader()
            for row in curs:
                writer.writerow({fieldnames[0]:row[0],fieldnames[1]:row[1],fieldnames[2]:row[2]})
                
            return
    
    
    def get_mxd(self,mxdname):
        """ взятие переменных проекта
        """
        mxd = arcpy.mapping.MapDocument(mxdname)
        layer = arcpy.mapping.ListLayers(mxd,'planted')[0]
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        layermiss = arcpy.mapping.ListLayers(mxd,'missing trees')[0]
        borders = arcpy.mapping.ListLayers(mxd,'borders')[0]
        background = arcpy.mapping.ListLayers(mxd,'background')[0]
        
        return mxd,layer,df,layermiss,borders,background


    def add_raster(self,filename, layerprefix=None, mxd='current'):
        """
        Adds raster image to mxd document.
        """
        if mxd is 'current':
            mxd, df = init()
        else:
            df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]
        #arcpy.env.workspace = tempfile.gettempdir()
        if layerprefix is not None:
            fn = layerprefix + os.path.basename(filename)[11:]
        else:
            fn = os.path.basename(filename)[11:]
        arcpy.MakeRasterLayer_management(filename, fn)
        #ext = arcpy.mapping.ListLayers(mxd, fn)[0].getExtent()
        #df.extent = ext
    
        return



    def saveMXD(self,path,name):
        tfolaer = os.path.join(inputshp[0],'MXDs')
        if not os.path.exists(tfolaer):
            os.makedirs(tfolaer)
        
        return


            
    def exportMap(self, shp, pathExport,mxds = True,csv = False):
        named = {'48777': 'Lao Che Clark Blk', '48776': 'Indiana McDonald', '48775': 'Lao Che Yamhill Blk', '48774': 'Kazim East', '48773': 'Spalko', '48772': 'Belloq', '48771': 'Indiana Jefferson', '48770': 'Elsa West', '48769': 'Elsa East', '48779': 'Donovan East', '48778': 'Donovan West', '48780': 'Kazim West', '48781': 'Mutt'}
        shppath = shp[0] + '//' + shp[1] + '.shp'
        
        """
        """
        savemaxd = shp[0]# путь в папку для сохранение мксд, можем сменится иза создания дисолв
        mxd,layer,df,layermiss,borders,background  = self.get_mxd('Belloq.mxd')# вызов переменных
        layer.replaceDataSource(shp[0],'SHAPEFILE_WORKSPACE',shp[1])# замена шейп файла в мксд
        df.extent = layer.getSelectedExtent(True)
        df.scale = df.scale * 1.07
        fid = self.get_fid_from_filename(shp[1])
        print fid
        treesmiss = glob.glob(os.path.join(pathtofligt, "tree count","*{}**{}*.shp").format(str(fid),'missing'))[0]
        imagepath = glob.glob(os.path.join(pathtofligt,"registered","*{}**{}*.tif").format(str(fid),'VNIR'))[0]
        #lyr = arcpy.MakeRasterLayer_management(imagepath,'Background')
        border = glob.glob(os.path.join(pathtofligt,"field borders","*{}*.shp").format(str(fid)))[0]
        layermiss.replaceDataSource(os.path.dirname(treesmiss),'SHAPEFILE_WORKSPACE',os.path.basename(treesmiss)[:-4])
        borders.replaceDataSource(os.path.dirname(border),'SHAPEFILE_WORKSPACE',os.path.basename(border)[:-4])
        background.replaceDataSource(os.path.dirname(imagepath),'RASTER_WORKSPACE',os.path.basename(imagepath)[:-4])
        
        arcpy.RefreshTOC() 
        arcpy.RefreshActiveView()  
        
        elemList = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")# получение листа всех элементов лейаута
        for elem in elemList:
                if elem.name == "NewName":
                    try:
                        elem.text = named[str(fid)]
                    except:
                        elem.text = str(fid)
                    continue
                elif elem.name == "Total_trees":
                    try:
                        elem.text = self.get_acr(shppath)
                    except Exception as e:
                        print (e)
                elif elem.name == "Total_miss":
                    elem.text = self.get_acr(treesmiss)
                    
          
                    
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
        if csv:
            self.get_geometry_co_csv(shppath)
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



    def get_acr (self, path):
        total = arcpy.GetCount_management(path)
        return total[0]
    
    
    

    def getPdf (self, pathTofolder, listshp, pathExport, mapbook = False):
        if mapbook == True:
            mapbookpath = pathExport
            pathExport = os.environ["TMP"] + "\\Maps"
            if not os.path.exists(pathExport):
                os.makedirs(pathExport)
        #shpfiles = glob.glob(r"D:\Google drive\Freelancers\Projects\Special Projects - Production\Farm Digitization\**\digitized\*.shp")
        shpfiles = glob.glob(os.path.join(pathtofligt,"tree count\*.shp"))
        for shp in shpfiles:
            if 'missing trees' in os.path.basename(shp)[:-4]:
                continue
            
            shpPath = []
            shpPath.append(os.path.dirname(shp))
            shpPath.append(os.path.basename(shp)[:-4])
            #try:
            self.exportMap(shpPath, pathExport)
            #except Exception as e:
                #print (e)
                    
        if  mapbook == True:
            name = str(datetime.datetime.now())[0:13].replace('-', '')
            mapbookpath = mapbookpath + "\\" + name + ".pdf"
            self.getmapbook(pathExport, mapbookpath)

print ('Please insert path to the folder with flight')

pathtofligt = raw_input()  

print ('Please insert path to the output folder')

pathoutput = raw_input()  

#an example
pdf = MapToPDF()
listshp = []# лист имен шейп файлов которые обрабатывать
pdf.getPdf( pathtofligt,listshp, pathoutput , mapbook = False)


#D:\Sasha\Goodle_drive\Freelancers\Projects\FM Vegetation boundaries\FM_updateMerge
#D:\Sasha\Goodle_drive\Freelancers\Projects\FM Vegetation boundaries\FM_updated






