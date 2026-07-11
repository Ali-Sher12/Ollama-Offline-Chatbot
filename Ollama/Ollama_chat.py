import ollama
#from pydantic import BaseModel #for structuring, if needed sometime
from colorama import Fore, Style, init
import os
from datetime import datetime
from docx import Document
import Assisting_Scripts.file_selector as file_popup
import Assisting_Scripts.load_file as file_loader


myModels = ollama.list()
aliveTimes = ['5m','10m','30m','45m','60m',-1]
myMessages = []
rememberPrevDescisions = False
outputToFile = False
output_folder = "OutWrite Documents"

if __name__ == "__main__":

    ############################################################################
    ############################################################################
    ############################################################################
    print("")
    i=0
    for m in myModels.models:
        i+=1
        print(i," : ",m.model,)
    selected_model_index = int(input("\nSelect your desired model[1-10] : "))
    #getting word by word progress
    print("\n=================================")
    i=0    
    for time_ in aliveTimes:
        i+=1
        print(i," : ",time_,)
    alive_index = int(input("\nSelect your desired time[1-4] (-1 means no time limit): "))
    print("\n=================================")

    ############################################################################
    ############################################################################
    ############################################################################

    rememberPrevDescisions = input("\nRemember previous descisions/files? [y/n] ")
    if rememberPrevDescisions=='y':
        rememberPrevDescisions=True
    outputToFile = input("\nTransfer the output to a docx file too? [y/n] ")        
    if outputToFile=='y':
        outputToFile=True

    ############################################################################
    ############################################################################
    ############################################################################
    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%I-%M-%S_%p")
    doc = Document()
    os.system("cls")
    while True:
        combined_data = ""
        file_paths = []
        user_msg = input(Fore.BLUE + "\n\nUser : ")
        if "quit chat" in user_msg:
            break
        if "__noatt__" not in user_msg:     
            file_paths = file_popup.pick_files()
        else:
            user_msg = user_msg.replace("__noatt__","")

        if outputToFile == True:
            doc.add_paragraph("User : "+user_msg)

        if len(file_paths) > 0:
            for fileName in file_paths:
                print("File Attached -> "+fileName)
                if outputToFile == True:
                    doc.add_paragraph(fileName)
                fileContent = file_loader.load_file_ext(fileName)
                combined_data+=(fileContent+"\n")
        combined_data+=user_msg
        myMessages.append({'role' : 'user' , 'content' : combined_data})
        bot_msg = ollama.chat(model = myModels.models[selected_model_index-1].model,
                    messages = myMessages,
                    keep_alive = aliveTimes[alive_index-1],
                    stream=True
                    )

        print(" ")
        print(Fore.YELLOW + "Assistant : ",end='')
        bot_response = ""
        for bot_chunk in bot_msg:
            print(bot_chunk.message.content, end='', flush=True)
            bot_response+=(bot_chunk.message.content)
        if outputToFile == True:
            doc.add_paragraph("Assistant : "+bot_response)
            doc.add_paragraph("________________________________________________________________________________________________")
            doc.save(os.path.join(output_folder, f"chat_{timestamp}.docx"))

        if rememberPrevDescisions == True:
            myMessages.append({'role' : 'assistant' , 'content' : bot_response})
        else:
            myMessages.clear()

    print(Style.RESET_ALL)

input("\nPress Enter to continue...")
