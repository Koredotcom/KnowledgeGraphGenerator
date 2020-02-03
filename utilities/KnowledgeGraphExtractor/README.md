**kore.ai**

# KnowledgeGraphExtractor
Use Kore.ai's Knowledge Graph Extractor to generate Ontology Report.

[Overview](#Overview)<br>
[Prerequisites](#Prerequisites)<br>
[Configuration Steps](#Configuration-Steps)<br>
[Run KnowledgeGraph Generator](#Run-KnowledgeGraph-Generator)<br>
[Command Options](#Command-Options)<br>
[Option: langauge](#Option-language)<br>
[Option: type](#type)<br>
[Output details](#Output-details)<br>

## Overview

Kore.ai KnowledgeGraph Extractor enables you to generate Ontology report.
It takes extracted json of FAQ as input and generates json file of ontology report.
 


## Prerequisites

* **Python 3.6:** The KnowledgeGraph Extractor requires python 3.6. Can be downloaded from here: [https://www.python.org/downloads/](https://www.python.org/downloads/)

* **Virtual Environment:** It is advised to use virtual environment, instead of directly installing requirements in the system directly. Follow the steps mentioned here to setup virtual environment. [https://www.geeksforgeeks.org/creating-python-virtual-environment-windows-linux/](https://www.geeksforgeeks.org/creating-python-virtual-environment-windows-linux/)

## Configuration Steps

Configuring KnowledgeGraph Extractor involves the following major steps:

* **Step 1:** **Download the KnowledgeGraphGenerator from GitHub :** Find the repository here: [https://github.com/Koredotcom/KnowledgeGraphGenerator](https://github.com/Koredotcom/KnowledgeGraphGenerator)

* **Step 2:** **Activate virtual environment:** Execute the following command with required changes in it to activate the virtual environment 
       <br> `source virtual_environments_folder_location/virtualenv_name/bin/activate`<br>
   Once the virtual environemnt is activated, you should see virtual environment name at the start of every command in the console. Something like this
   ![Image alt text](https://github.com/Koredotcom/KnowledgeGraphGenerator/blob/master/blob/venv.png)
   
* **Step 3:** **Change root directory to utilities/KnowledgeGraphExtractor/** Run the following command from your project root directory (KnowledgeGraphGenerator) to change directory
    <br> cd utilities/KnowledgGraphExtractor/
    
* **Step 4:** **Install requirements for the project:** Run the following command from current directory (KnowledgeGraphExtractor) to install requirements
   <br> `pip install -r requirements.txt`<br>
    Run <br>`pip list`<br> command to verify is all the installed requirements
    
    ### Note - <br>
    **For Windows Operating System -** 
    <ol>
      <li>Windows 10 users should install Windows 10 SDK. You can download it from here <a href="https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk/"> here</a><br></li>
     <li>Operating system should be upto date for seamless installation of requirements. Some libraries like scipy (internal dependency) need specific dll's which are available in latest updates. Avoiding this may involve lot of troubleshooting. 
 <br> We verified installation with build version 1903.
     </li>
 </ol>

## Run KnowledgeGraph Extractor
Command - `python  ontology_analyzer.py --file_path 'INPUT_FILE_PATH' --language 'LANGUAGE_CODE'` <br>

The command which generates Ontology Report have options which need to be passed while executing the command. The following are the options which are used.<br>

## Command Options

**Note: : The options which are listed as mandatory should be given along with  command, for options which are regarded as optional, the default values mentioned will be picked**

<table>
       <tr>
              <td> Option name </td>
              <td> Description </td>
              <td> Mandatory / Optional </td>
              <td> Default value </td>
       <tr>
       <tr>
              <td> --file_path </td>
              <td> Input file location </td>
              <td> Mandatory </td> 
              <td></td>
       </tr>
       <tr>
              <td> --language </td>
              <td> The language code for langauge in which input data exist </td>
              <td> Optional </td>
              <td> en (english) </td>
       </tr>
</table>

### Option: langauge 

The following languages are supported currently and others will be added in incremental approach. Create an issue if any language is required on priority

<table>
       <tr>
              <td> Language </td>
              <td>Language Code </td>
       </tr>
       <tr>
              <td> English </td>
              <td> en </td>
       </tr>
</table>

## Output details

Output JSON file generated can be located under project root directory with name of file as `inputfilenameReport.json` <br>

   
