import ollama
from pydantic import BaseModel #for structuring
import Reading_Scripts.load_csv
import Reading_Scripts.load_docx
import Reading_Scripts.load_pdf
import Reading_Scripts.load_pptx
import Reading_Scripts.load_xlsx
import Reading_Scripts.load_txt

myModels = ollama.list()
aliveTimes = ['10m','30m','45m','60m',-1]

myMessages = []

if __name__ == "__main__":
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

    while True:
        user_msg = input("\n\nUser: ")
        if "quit chat" in user_msg:
            break
        myMessages.append({'role' : 'user' , 'content' : user_msg})
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
        myMessages.append({'role' : 'assistant' , 'content' : bot_response})        
