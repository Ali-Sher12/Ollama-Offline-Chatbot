import ollama
import os

myModels = [
    "llama3.2:1b",
    "llama3.2:3b",
    "llama3.1:8b",
    "phi3",
    "phi3:mini",
    "qwen2.5-coder:7b",
    "gemma3",
    "gemma4:e2b",
    "deepseek-r1:1.5b",
    "mistral"
]
aliveTimes = ['10m','30m','45m','60m',-1]

myMessages = []

if __name__ == "__main__":
    i=0
    for model in myModels:
        i+=1
        print(i," : ",model,)
    selected_model_index = int(input("Select your desired model[1-10] : "))
    #getting word by word progress
    i=0    
    for time_ in aliveTimes:
        i+=1
        print(i," : ",time_,)
    alive_index = int(input("Select your desired time[1-4] : "))

    for progress in ollama.pull(myModels[selected_model_index-1], stream=True):
        os.system('cls');
        print(progress)
    print("Model ",myModels[selected_model_index-1]," Successfully Loaded")

    while True:
        user_msg = input("\n\nUser: ")
        if "quit chat" in user_msg:
            break
        myMessages.append({'role' : 'user' , 'content' : user_msg})
        bot_msg = ollama.chat(model=myModels[selected_model_index-1],
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
