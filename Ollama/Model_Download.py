import ollama
import os

myModels = [
    "llama3.2:1b",
    "llama3.2:3b",
    "llama3.1:8b",
    "phi3",
    "phi3:mini",
    "qwen2.5:3b-instruct",
    "dolphin-mistral",
    "qwen2.5-coder:7b",
    "gemma3",
    "gemma4:e2b",
    "deepseek-r1:1.5b",
    "mistral"
]
if __name__ == "__main__":
    i=0
    for model in myModels:
        i+=1
        print(i," : ",model,)
    selected_model_index = list(map(int, input("Enter Your desired model indices: ").split()))
    for num in selected_model_index:
        for progress in ollama.pull(myModels[num-1], stream=True):
            print(progress)
        print("\nModel ",myModels[num-1]," Successfully Downloaded.\n")