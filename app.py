from __future__ import annotations
import PySimpleGUI as sg
import pydicom
from dicompylercore import dicomparser, dvh, dvhcalc
import warnings
from pathlib import Path
import pyperclip
from zipfile import ZipFile
import glob

warnings.filterwarnings("ignore", category=RuntimeWarning)

sg.theme('Dark')

### FUNCTION LIST ##
def get_dicomfiles(zip_fp: str) -> tuple[list, list]:
    struc_files = []
    dose_files = []
    with ZipFile(zip_fp, 'r') as zip:
        files = [name for name in zip.namelist() if name.endswith('.dcm')]
        for file in files:
            ds = pydicom.read_file(zip.open(file))
            if ds.file_meta.MediaStorageSOPClassUID.name == 'RT Structure Set Storage':
                struc_files.append(file)
            elif ds.file_meta.MediaStorageSOPClassUID.name == 'RT Dose Storage':
                dose_files.append(file)
        
    return struc_files, dose_files

def read_analysis_config(analysis_fp: str) -> dict:
    analysis_dictionary = {}
    with open("configs\\" + analysis_fp + ".txt", 'r') as file:
        lines = file.readlines()
        for line in lines:
            if line.split(':')[0] not in analysis_dictionary:
                analysis_dictionary[line.split(':')[0]] = []
            analysis_dictionary[line.split(':')[0]].append(line.split(':')[1].strip("\n"))
    return analysis_dictionary

def get_structure_index(zip_fp: str, struc_fp: str, struc_name: str, aliases: dict) -> int:
    index = None
    # Add aliases for searching
    if struc_name in aliases:
        struc_names = aliases[struc_name]
        struc_names.insert(0,struc_name)
    else:
        struc_names = [struc_name]
    
    with ZipFile(zip_fp, 'r') as zip:
        ds = dicomparser.DicomParser(pydicom.read_file(zip.open(struc_fp)))
        structures = ds.GetStructures()
        for name in struc_names:
            for entry in ds.GetStructures():
                if structures[entry]['name'] == name:
                    index = structures[entry]['id']
                    return index
    return index

def get_structure_list(zip_fp: str, struc_fp: str) -> list:
    list = []
    with ZipFile(zip_fp, 'r') as zip:
        ds = dicomparser.DicomParser(pydicom.read_file(zip.open(struc_fp)))
        structures = ds.GetStructures()
        for entry in ds.GetStructures():
            list.append(structures[entry]['name'])
    return list

def get_study_description(zip_fp: str, dicom_fp: str) -> str:
    with ZipFile(zip_fp, 'r') as zip:
        try:
            description = pydicom.read_file(zip.open(dicom_fp)).StudyDescription
        except AttributeError:
            description = '### REMOVED ###'
    return description

def get_dvh(zip_fp: str, struc_fp: str, dose_fp: str, index: int, display: str) -> dvh:
    with ZipFile(zip_fp, 'r') as zip:
        calcdvh = dvhcalc.get_dvh(pydicom.read_file(zip.open(struc_fp)), pydicom.read_file(zip.open(dose_fp)), index)
    return calcdvh

def get_dose_metrics(zip_fp: str, struc_fp: str, dose_fp: str, analysis_fp: str, result_settings: dict) -> tuple[dict, str]:
    message = ""
    results_dictionary = {}
    dvh_dictionary = {}
    rx_prescription = result_settings["rx_prescription"]
    analysis_dictionary = read_analysis_config(analysis_fp)
    for structure in analysis_dictionary:
        results_dictionary[structure] = {}
        index = get_structure_index(zip_fp, struc_fp, structure, result_settings["aliases"])
        if index is None:
            for metric in analysis_dictionary[structure]:
                results_dictionary[structure][metric] = (-1,'N/A')
            message = "Some structures not found!"
            continue
        dvh_dictionary[structure] = get_dvh(zip_fp, struc_fp, dose_fp, index, result_settings)
        for metric in analysis_dictionary[structure]:
            if metric == "VOL":
                results_dictionary[structure][metric] = (dvh_dictionary[structure].volume, 'cm3')
            elif not result_settings["relative"]: 
                results_dictionary[structure][metric] = (dvh_dictionary[structure].statistic(metric).value, dvh_dictionary[structure].statistic(metric).units)
            else:
                if metric.startswith('V'):
                    results_dictionary[structure][metric] = ((dvh_dictionary[structure].statistic(metric).value/dvh_dictionary[structure].volume)*100, '%')
                if metric.startswith('D'):
                    results_dictionary[structure][metric] = ((dvh_dictionary[structure].statistic(metric).value/rx_prescription)*100, '%')
    if message == "":
        message = "Analyse Complete"
    return results_dictionary, message

### GUI COLOUMN DESIGNS ###

# sections
file_list_column = [
    [
        sg.Text("DICOM Zip:"),
        sg.In(size=(35, 1), enable_events=True, key="-ZIP-"),
        sg.FileBrowse(file_types=(("Zip Files", "*.zip"),)),
    ],
    [
        sg.Text("Structure DICOM File:", font=('bold'))
    ],
    [
        sg.Listbox(
            values=[], enable_events=True, size=(60, 10), key="-STRUCTURE LIST-"
        )
    ],
    [
        sg.Text("Dose DICOM File:", font=('bold'))
    ],
    [
        sg.Listbox(
            values=[], enable_events=True, size=(60, 10), key="-DOSE LIST-"
        )
    ],
    [
        sg.Text('Dose Study Description:    '),
        sg.Text(size=(35, 1), key='-DOSE DESC-')
    ],
    [
        sg.Text("Analysis:", font=('bold'))
    ],
    [
        sg.Text("Analysis Config File:"),
        sg.Combo(
            values=[name.split('\\')[-1].split('.txt')[0] for name in glob.glob('configs\*.txt')], \
                enable_events=True, size=(30, 10), key="-CONFIG-", \
                default_value=[name.split('\\')[-1].split('.txt')[0] for name in glob.glob('configs\*.txt')][0])
    ],
    [
        sg.Text("Display as:"),
        sg.Radio('Absolute', 1, enable_events=True, key='-ABSOLUTE-'),
        sg.Radio('Relative', 1, default=True, enable_events=True, key='-RELATIVE-')
    ],
    [
        sg.Button('See Structures', key='-STRUC LIST-'),
        sg.Button('Set Prescription', key='-SET PRESCRIPTION-'),
        sg.Button('Set Alias', key='-SET ALIAS-'),
        sg.Button('Run Analysis', key='-ANALYSE-'),
    ],
    [
        sg.Text("Reporting:", font=('bold'))
    ],
    [
        sg.Button('Copy All', key='-COPY ALL-'),
        sg.Button('Copy Values', key='-COPY VALUES-'),
        sg.Button('Show Aliases', key='-SHOW ALIASES-'),
    ],
    [
        sg.Text('Status:    '),
        sg.Text(size=(35, 1), key='-STATUS-')
    ],
]

# For now will only show the name of the file that was chosen
result_viewer_column = [
    [sg.Text("Results:", font=('bold'))],
    [sg.Table(values=[], headings=['STRUCTURE','METRIC','VALUE','UNIT'],
    num_rows=40,
    display_row_numbers=False,
    justification='top', key='-TABLE-', 
    selected_row_colors='red on yellow',
   )]
]

### LAYOUT SPECIFICATION ###
layout = [
    [
        sg.Column(file_list_column),
        sg.VSeperator(),
        sg.Column(result_viewer_column),
    ]
]

window = sg.Window("DVH Stat Grab", layout, resizable=True)
result_settings = {'relative': True, 'rx_prescription': -1.0, 'aliases': {}}
results = {}

### EVENT LOOP ###
while True:
    event, values = window.read()
    #print(event)
    if event == "Exit" or event == sg.WIN_CLOSED:
        break
    # Folder name was filled in, make a list of files in the folder
    if event == "-ZIP-":
        file_path = values["-ZIP-"]
        window["-STATUS-"].update("Loading ZIP file...")
        struc_files, dose_files = get_dicomfiles(file_path)
        window["-STRUCTURE LIST-"].update(struc_files)
        window["-DOSE LIST-"].update(dose_files)
        window["-STATUS-"].update(f"Finished reading zip file.", background_color='green')

    elif event == "-STRUCTURE LIST-":  # A file was chosen from the listbox
        pass
                
    elif event == "-DOSE LIST-":  # A file was chosen from the listbox
        window["-DOSE DESC-"].update(get_study_description(values["-ZIP-"], values["-DOSE LIST-"][0]))

    elif event == "-ANALYSE-":
        if len(values["-STRUCTURE LIST-"]) > 0 and len(values["-DOSE LIST-"]) > 0:
            window["-STATUS-"].update(f"Analysing...")
            results, message = get_dose_metrics(values["-ZIP-"], values["-STRUCTURE LIST-"][0], values["-DOSE LIST-"][0], values['-CONFIG-'], result_settings)
            table_results = []
            for structure in results:
                for metric, value in results[structure].items():
                    table_results.append([structure, metric, value[0], value[1]])
            window["-TABLE-"].update(table_results)
            if message == "Analyse Complete":
                window["-STATUS-"].update(message, background_color='green')
            else:
                window["-STATUS-"].update(message, background_color='red')
        else:
            window["-STATUS-"].update("Select both a dose and structure file", background_color='red')
    
    elif event == "-STRUC LIST-":
        if len(values["-STRUCTURE LIST-"]) > 0:
            struc_list = get_structure_list(values["-ZIP-"], values["-STRUCTURE LIST-"][0])
            sg.popup_scrolled("\n".join(struc_list), title="Structures")
        else:
            window["-STATUS-"].update(f"Select structure set first", background_color='red')
    
    elif event == "-SET PRESCRIPTION-":
        try:
            result_settings['rx_prescription'] = float(sg.popup_get_text('Enter the prescription dose (Gy):', title='Set Prescription'))
            window["-STATUS-"].update(f"Set prescription to: {result_settings['rx_prescription']}Gy", background_color='green')        
        except ValueError:
            window["-STATUS-"].update(f"Prescription needs to be numeric", background_color='red')
            
    elif event == "-SET ALIAS-":
        try:
            text = sg.popup_get_text('alias=structure:', title='Set Alias')
            if text.split('=')[1] not in result_settings['aliases']:
                result_settings['aliases'][text.split('=')[1]] = []
            result_settings['aliases'][text.split('=')[1]].append(text.split('=')[0])
            window["-STATUS-"].update(f"Added alias: {text}", background_color='green')        
        except:
            window["-STATUS-"].update(f"Format should be: alias=structure", background_color='red')
    
    elif event == "-ABSOLUTE-":
        result_settings["relative"] = False
        window["-STATUS-"].update(f"Results set to: absolute", background_color='green')
        
    elif event == "-RELATIVE-":
        result_settings["relative"] = True
        window["-STATUS-"].update(f"Results set to: relative", background_color='green')

    elif event == "-COPY ALL-":
        if results != {}:
            text = ""
            for structure in results:
                    for metric, value in results[structure].items():
                        text+=f"{structure},{metric},{value[0]},{value[1]}\n"
            pyperclip.copy(text)
            window["-STATUS-"].update(f"Copied to clipboard", background_color='green')
        else:
            window["-STATUS-"].update(f"Need to analyse first", background_color='red')
    
    elif event == "-COPY VALUES-":
        if results != {}:
            text = ""
            for structure in results:
                    for metric, value in results[structure].items():
                        text+=f"{value[0]},"
            pyperclip.copy(text[:-1]) # remove last comma
            window["-STATUS-"].update(f"Copied to clipboard", background_color='green')
        else:
            window["-STATUS-"].update(f"Need to analyse first", background_color='red')
            
    elif event == "-SHOW ALIASES-":
        text = ""
        if result_settings["aliases"] != {}:
            for alias in result_settings["aliases"]:
                for entry in result_settings["aliases"][alias]:
                    text += f"{entry}={alias}\n"
            sg.popup_scrolled(text[:-1], title="Aliases")
        else:
            window["-STATUS-"].update(f"No alises have been set", background_color='red')
            
window.close()
