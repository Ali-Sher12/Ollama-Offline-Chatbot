import ollama
#from pydantic import BaseModel #for structuring, if needed sometime
import os
from datetime import datetime
from docx import Document
import Assisting_Scripts.file_selector as file_popup
import Assisting_Scripts.load_file as file_loader


myModels = ollama.list()
aliveTimes = ['10m','30m','45m','60m',-1]
myMessages = []
rememberPrevDescisions = False
outputToFile = False
output_folder = "OutWrite Documents"

if __name__ == "__main__":

    ############################################################################
    ############################################################################
    ############################################################################

    i=0
    for m in myModels.models:
        i+=1
        print(i," : ",m.model,)
    selected_model_index = int(input("Select your desired model[1-10] : "))
    #getting word by word progress
    print("\n")
    i=0    
    for time_ in aliveTimes:
        i+=1
        print(i," : ",time_,)
    alive_index = int(input("Select your desired time[1-4] (-1 means no time limit): "))

    ############################################################################
    ############################################################################
    ############################################################################

    rememberPrevDescisions = input("Remember previous descisions/files? [y/n] ")
    if rememberPrevDescisions=='y':
        rememberPrevDescisions=True
    outputToFile = input("Transfer the output to a docx file too? [y/n] ")        
    if outputToFile=='y':
        outputToFile=True

    ############################################################################
    ############################################################################
    ############################################################################
    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%I-%M-%S_%p")
    doc = Document()
    while True:

        user_msg = input("\n\nUser: ")
        if "quit chat" in user_msg:
            break
        if outputToFile == True:
            doc.add_paragraph(user_msg)        
        file_paths = file_popup.pick_files()
        myMessages.append({'role' : 'user' , 'content' : user_msg})        
        if len(file_paths) > 0:
            for fileName in file_paths:
                if outputToFile == True:
                    doc.add_paragraph(fileName)
                fileContent = file_loader.load_file_ext(fileName)
                myMessages.append({'role' : 'user' , 'content' : fileContent})

        bot_msg = ollama.chat(model = myModels.models[selected_model_index-1].model,
                    messages = myMessages,
                    keep_alive = aliveTimes[alive_index-1],
                    stream=True
                    )

        print("\n")
        bot_response = ""
        for bot_chunk in bot_msg:
            print(bot_chunk.message.content, end='', flush=True)
            bot_response+=(bot_chunk.message.content)
        if outputToFile == True:
            doc.add_paragraph(bot_response)
            doc.save(os.path.join(output_folder, f"chat_{timestamp}.docx"))

        if rememberPrevDescisions == True:
            myMessages.append({'role' : 'assistant' , 'content' : bot_response})
        else:
            myMessages.clear()

