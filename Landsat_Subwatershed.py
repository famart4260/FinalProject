import os, shutil, glob, arcpy
arcpy.CheckOutExtension("spatial")

# Overwrite pre-existing files
arcpy.env.overwriteOutput = True

Working_dir = 'D:\Python\Project\LLW'
AOI = 'D:\Python\Project\LLW\Shapefile\LLWatershed.shp'


Landsat_folder = Working_dir + '\Landsat'
Output_folder = Working_dir + '\Output'
if not os.path.exists(Output_folder):
    os.makedirs(Output_folder)


### Composite Bands ###
for Lfolder in glob.glob(Landsat_folder + '\*'):
    Composite_list = []
    for name in glob.glob(Lfolder + '\*.tif'):

        # Seperate the file path and the filename
        fpath, fname_wtif = os.path.split(name)

        # Get the .tif out of the file name
        fname = fname_wtif.split('.')[0]
        Landsat_name = "_".join(fname.split('_')[:-3])
                
        # Create oupput composite folder
        Composite_Band_folder = Output_folder + '\CompositeBand'
        if not os.path.exists(Composite_Band_folder):
            os.makedirs(Composite_Band_folder)
        
        # Create oupput composite raster name
        out_comp = Composite_Band_folder + '\\' + Landsat_name + '_composite.tif'
        # Select the bands that need to be composited
        
        if name.endswith(('B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF', 'B6.TIF', 'B7.TIF')):
            Composite_list.append(name)

    print Landsat_name + " is being processed."
    arcpy.CompositeBands_management(Composite_list, out_comp)
print("")


### Clip the composite landsat image to the Lake Lanier Watershed ###
# Create oupput Clip LLWatershed folder
Clip_LLWatershed_folder = Output_folder + '\LLWatershedClip'
if not os.path.exists(Clip_LLWatershed_folder):
    os.makedirs(Clip_LLWatershed_folder)
    
for comp_name in glob.glob(Composite_Band_folder + '\*.tif'):
    # Seperate the file path and the filename
    cpath, cname_wtif = os.path.split(comp_name)

    # Get the .tif out of the file name 
    Composite_name = cname_wtif.split('.')[0]
    out_composite_clip = Clip_LLWatershed_folder + '\\' + Composite_name + '_clip.tif'
           
    print cname_wtif + " is being processed."
    arcpy.gp.ExtractByMask_sa(comp_name, AOI, out_composite_clip)
print("")

### Unsupervised Classification ###
Unsupervised_Classification_folder = Output_folder + '\UnsupervisedClassification'
if not os.path.exists(Unsupervised_Classification_folder):
    os.makedirs(Unsupervised_Classification_folder)

for clip_name in glob.glob(Clip_LLWatershed_folder + '\*.tif'):
    # Seperate the file path and the filename
    clip_path, clip_name_wtif = os.path.split(clip_name)

    # Get the .tif out of the file name 
    UC_name = clip_name_wtif.split('.')[0]

    # Set parameters for ISO Unsupervised Classification
    out_UC = Unsupervised_Classification_folder + '\\' + UC_name + '_uc.tif'
    number_of_classes = "5"
    minimum_class_size = "20"
    sample_interval = "10"
    Output_signature_file = ""
    
    # Process: Iso Cluster Unsupervised Classification      
    print clip_name_wtif + " is being processed."
    arcpy.gp.IsoClusterUnsupervisedClassification_sa(clip_name,
                                                     number_of_classes,
                                                     out_UC,
                                                     minimum_class_size,
                                                     sample_interval,
                                                     Output_signature_file)
print("")



### Calculate Land Use pixels ###

Summarized_Stat_folder = Output_folder + '\SummarizedStat'
if not os.path.exists(Summarized_Stat_folder):
    os.makedirs(Summarized_Stat_folder)

for sub_name in glob.glob(Unsupervised_Classification_folder + '\*.tif'):
    # Seperate the file path and the filename
    sub_path, sub_wtif = os.path.split(sub_name)

    # Get the .tif out of the file name 
    s_name = sub_wtif.split('.')[0]
    Landsat_Year = s_name[17:21]
    Landsat_Month = s_name[21:23]
    subbasin_num = s_name[-1]
  
    # Set parameters for ISO Unsupervised Classification
    out_summarized_dbf = Summarized_Stat_folder + '\\' + s_name + '.dbf'
    
    # Process: Summary Statistics
    arcpy.Statistics_analysis(sub_name, out_summarized_dbf, "OID FIRST", "Value;Count")

    # Process: Delete Field
    arcpy.DeleteField_management(out_summarized_dbf, "FREQUENCY;FIRST_OID")

    # Process: Add Field 
    arcpy.AddField_management(out_summarized_dbf, "LandUse", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field 
    arcpy.CalculateField_management(out_summarized_dbf, "LandUse", "Reclass(!Value!, !LandUse!)", "PYTHON", "def Reclass(Value, LandUse):\\n    if  Value == 1:\\n        return 'Water_WL'\\n    elif  Value == 2:\\n        return 'Forest'\\n    elif Value == 3:\\n        return 'Grass'\\n    elif Value == 4:\\n        return 'AgrLand'\\n    elif Value == 5:\\n      return 'URS'")

    # Process: Add Field
    arcpy.AddField_management(out_summarized_dbf, "PivotID", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field
    arcpy.CalculateField_management(out_summarized_dbf, "PivotID", "1", "PYTHON_9.3", "")

    # Process: Pivot Table
    out_pivot_table = Summarized_Stat_folder + '\\' + s_name + '_pivot.dbf'
    arcpy.PivotTable_management(out_summarized_dbf, "PivotID", "LandUse", "Count", out_pivot_table)

    LU_lst = ["AgrLand", "URS", "Grass", "Forest", "Water_WL"]
    for landuse in LU_lst:
        pivot_column = arcpy.ListFields(out_pivot_table, landuse)
        if len(pivot_column) != 1:
            arcpy.AddField_management(out_pivot_table, landuse, "DOUBLE", "", "", "", "", "NON_NULLABLE", "NON_REQUIRED", "")
            arcpy.CalculateField_management(out_pivot_table, landuse, "0", "PYTHON_9.3", "")

    # Process: Summary Statistics
    out_for_combine_dbf = Summarized_Stat_folder + '\\' + s_name + '_forCombine.dbf'
    arcpy.Statistics_analysis(out_pivot_table, out_for_combine_dbf, "AgrLand MAX;Forest MAX;Grass MAX;URS MAX;Water_WL MAX", "OID")

    # Process: Add Field
    arcpy.AddField_management(out_for_combine_dbf, "LYear", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field 
    arcpy.CalculateField_management(out_for_combine_dbf, "LYear", '"' + Landsat_Year + '"', "PYTHON")

    # Process: Add Field
    arcpy.AddField_management(out_for_combine_dbf, "LMonth", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field 
    arcpy.CalculateField_management(out_for_combine_dbf, "LMonth", '"' + Landsat_Month + '"', "PYTHON")
    
    # Process: Add Field
    arcpy.AddField_management(out_for_combine_dbf, "Water_WL", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field
    arcpy.CalculateField_management(out_for_combine_dbf, "Water_WL", "!MAX_Water_!", "PYTHON_9.3", "")

    # Process: Delete Field
    arcpy.DeleteField_management(out_for_combine_dbf, "MAX_Water_")

    # Process: Add Field
    arcpy.AddField_management(out_for_combine_dbf, "Forest", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field
    arcpy.CalculateField_management(out_for_combine_dbf, "Forest", "!MAX_Forest!", "PYTHON_9.3", "")

    # Process: Delete Field
    arcpy.DeleteField_management(out_for_combine_dbf, "MAX_Forest")
    
    # Process: Add Field
    arcpy.AddField_management(out_for_combine_dbf, "Grassland", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field
    arcpy.CalculateField_management(out_for_combine_dbf, "Grassland", "!MAX_Grass!", "PYTHON_9.3", "")

    # Process: Delete Field
    arcpy.DeleteField_management(out_for_combine_dbf, "MAX_Grass")

    # Process: Add Field
    arcpy.AddField_management(out_for_combine_dbf, "URS", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field
    arcpy.CalculateField_management(out_for_combine_dbf, "URS", "!MAX_URS!", "PYTHON_9.3", "")

    # Process: Delete Field
    arcpy.DeleteField_management(out_for_combine_dbf, "MAX_URS")

    # Process: Add Field
    arcpy.AddField_management(out_for_combine_dbf, "CropLand", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Process: Calculate Field
    arcpy.CalculateField_management(out_for_combine_dbf, "CropLand", "!MAX_AgrLan!", "PYTHON_9.3", "")

    # Process: Delete Field
    arcpy.DeleteField_management(out_for_combine_dbf, "MAX_AgrLan")
    
    # Process: Delete Field 
    arcpy.DeleteField_management(out_for_combine_dbf, "FREQUENCY")

    print(s_name + ' table is ready.')
print("")

Summarized_Stat_folder = Output_folder + '\SummarizedStat'
print('Combing dbf...')
### Combine summarized table into a single table ###
combine_folder = Summarized_Stat_folder + '\dbf_combine'
if not os.path.exists(combine_folder):
    os.makedirs(combine_folder)
for combine_dbf in glob.glob(Summarized_Stat_folder + '/*.dbf'):
    if combine_dbf.endswith("forCombine.dbf"):
        shutil.copy(combine_dbf, combine_folder)

# Combine dbf
arcpy.env.workspace = combine_folder
tableList = arcpy.ListTables()
final_dbf = combine_folder + '\Summarized.dbf'
arcpy.Merge_management(tableList, final_dbf)
print('Combing dbf is done!')
print("")

# Export to xls
final_xls = Output_folder + '\Summarized.xls'
arcpy.TableToExcel_conversion(final_dbf,
                              final_xls ,
                              "ALIAS",
                              "CODE")
print('Finished exporting to xls!')
print("")

arcpy.CheckInExtension("spatial")   
print("Done")
