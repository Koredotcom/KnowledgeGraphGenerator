**kore.ai**

# KnowledgeGraphGenerator
Use Kore.ai's Knowledge Graph Generator to automatically extract terms from FAQs, define the hierarchy between these terms, and also associate the FAQs to the right terms.

[Overview](#Overview)<br>
[Prerequisites](#Prerequisites)<br>
[Configuration Steps](#Configuration-Steps)<br>
[Run KnowledgeGraph Generator](#Run-KnowledgeGraph-Generator)<br>
[Command Options](#Command-Options)<br>
[Option: langauge](#Option-language)<br>
[Option: type](#type)<br>
[Output details](#Output-details)<br>
[Graph analyzer](#Graph-analyzer)<br>
[Troubleshooting](#Troubleshooting)<br>

## Overview

Kore.ai KnowledgeGraph Generator enables you to cut down your effort in building ontology in Knowledge Collection section by automating this process.
 
Output generated through this engine can be directly imported in KnowledgeCollection and you can use the faqs after training the KnowledgeCollection. However, user should manually add synonyms if he wants to. Since the engine won't support this yet.

If you have managed your stopwords the engine will consider only those stopwords in generating the graph considering the fact that you pass JSON or CSV export directly. If CSV format from extraction type is given as input or user haven't modified stopword collection, Engine uses it's predefined set of stopwords

## Prerequisites

* **Python 3.6:** The KnowledgeGraph Generator requires python 3.6. Can be downloaded from here: [https://www.python.org/downloads/](https://www.python.org/downloads/)

* **Virtual Environment:** It is advised to use virtual environment, instead of directly installing requirements in the system directly. Follow the steps mentioned here to setup virtual environment. [https://www.geeksforgeeks.org/creating-python-virtual-environment-windows-linux/](https://www.geeksforgeeks.org/creating-python-virtual-environment-windows-linux/)

## Configuration Steps

Configuring KnowledgeGraph Generator involves the following major steps:

* **Step 1:** **Download the KnowledgeGraphGenerator from GitHub :** Find the repository here: [https://github.com/Koredotcom/KnowledgeGraphGenerator](https://github.com/Koredotcom/KnowledgeGraphGenerator)

* **Step 2:** **Activate virtual environment:** Execute the following command with required changes in it to activate the virtual environment 
       <br> `source virtual_environments_folder_location/virtualenv_name/bin/activate`<br>
   Once the virtual environemnt is activated, you should see virtual environment name at the start of every command in the console. Something like this
   ![Image alt text](https://github.com/Koredotcom/KnowledgeGraphGenerator/blob/master/blob/venv.png)
   
* **Step 3:** **Install requirements for the project:** Run the following command from your project root directory (KnowledgeGraphGenerator) to install requirements
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
              

* **Step 4.** **Download spacy english model:** Run following command to download the model 
     <br>`python -m spacy download en`<br>

## Run KnowledgeGraph Generator
Command - `python  KnowledgeGraphGenerator.py --file_path 'INPUT_FILE_PATH' --type 'INPUT_TYPE' --language 'LANGUAGE_CODE' --v true` <br>

The command which generates KnowledgeGraph have options which need to be passed while executing the command. The following are the options which are used.<br>

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
       <tr>
              <td> --type </td>
              <td> The type of input file 
                     <ol>
                            <li>json_export</li>
                            <li>csv</li>
                            <li> csv_export </li>
                     </ol>
              </td>
              <td> Mandatory </td>
              <td></td>
       </tr>
       <tr>
              <td> --v</td>
              <td> Running command in verbose mode to see intermediate progress steps </td>
              <td> Optional </td>
              <td> false <td>
       <tr>
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

### Option: type

Type specifies the type of input file. Currently only three formats are supported and those are listed below: <br>
<ol>
       <li>
              <strong> json_export - </strong> <p>You can generate input in this format from kore.ai bot builder tool by exporting KnowledgeCollection and selecting JSON format for export </p>
       </li>
       <li> 
              <strong> csv_export - </strong> <p>You can generate input int this format from kore.ai bot builder tool by exporting KnowledgeCollection and selecting CSV format for export </p>
       </li>
       <li>
              <strong> csv - </strong> <p> This format is enabled to support input from KnowledgeExtraction. To build input file in this format, all you need to do is copy all questions in <b>first column</b> and their respective answers in <b>second column</b> and save it as .csv file
       </li>
</ol>

## Output details

Output JSON file generated can be located under project root directory with name of file as `ao_output.json` <br>

The output JSON file can be <b> directly imported to KnowledgeCollection in bot </b> as json format

## Graph analyzer
Graph generated by the tool may not meet human expectations. After graph is generated, the generated graph is analyzed by our analyzer tool which helps in identifying errors which results due to input data, the way it is. We may have two issues while preparing the graph.

### Unreachable Questions

First one, the alternate questions which are part of the input primary questions in input export, will be mapped to same questions again. This is due to preserve the question-alternate question relation that was given previously. This may lead to less path coverage for alternate questions as the terms built for primary question will also be part of its alternate questions. 

### Questions at root node

Second one, the questions which are very dissimilar in corpus may not get grouped. These questions are placed in root node. Its bot developers responsibility to group them, the way they want.<br>

The output from analyzer is a CSV file which shows error type and questions under that error. The path to reach the question is also available in the CSV. Following, is the sample analyzer CSV <br>

   ![Image alt text](https://github.com/Koredotcom/KnowledgeGraphGenerator/blob/master/blob/analyzer.png)


## Troubleshooting
 ### Windows Operating system
  [Cannot open include fil
e: 'basetsd.h': No such file or directory](https://stackoverflow.com/questions/23691564/running-cython-in-windows-x64-fatal-error-c1083-cannot-open-include-file-ba) <br>
  
  <p> C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\BIN\amd64\cl.exe /c /nolog
o /Ox /MD /W3 /GS- /DNDEBUG -IC:\Python27\include -IC:\Python27\PC /Tchello.c /F
obuild\temp.win-amd64-2.7\Release\hello.obj
hello.c
C:\Python27\include\pyconfig.h(227) : fatal error C1083: Cannot open include fil
e: 'basetsd.h': No such file or directory
error: command '"C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\BIN\amd64
\cl.exe"' failed with exit status 2 </p>

   [LNK1158 cannot run rc.exe x64 Visual Studio](https://stackoverflow.com/questions/35215971/lnk1158-cannot-run-rc-exe-x64-visual-studio) <br>
   
   
   
