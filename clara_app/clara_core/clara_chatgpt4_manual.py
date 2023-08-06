from .clara_classes import *
import tkinter as tk
import time

# Example usage
# get_chatgpt_response("Translate the following English text to French: 'Hello, how are you?'")

import tkinter as tk
import tkinter.scrolledtext as st

def get_chatgpt4_response(prompt):
    def submit():
        response_text.set(response_entry.get("1.0", tk.END))
        window.quit()

    start_time = time.time()
    window = tk.Tk()
    window.title("ChatGPT-4 Manual Interaction")

    prompt_label = tk.Label(window, text="Prompt:")
    prompt_label.pack(pady=(20, 10))

    prompt_entry = st.ScrolledText(window, width=80, height=10, wrap=tk.WORD)
    prompt_entry.insert(tk.END, prompt)
    prompt_entry.configure({"background": "white", "state": "disabled"})
    prompt_entry.pack(pady=(0, 10))

    response_label = tk.Label(window, text="Paste ChatGPT-4 Response Here:")
    response_label.pack(pady=(20, 5))

    response_entry = tk.Text(window, width=80, height=10)
    response_entry.pack(pady=(0, 10))

    submit_button = tk.Button(window, text="Submit", command=submit)
    submit_button.pack(pady=(10, 20))

    response_text = tk.StringVar()

    window.mainloop()
    window.destroy()

    response_string = response_text.get()
    cost = 0.0
    elapsed_time = time.time() - start_time

    # Create an APICall object
    api_call = APICall(
        prompt=prompt,
        response=response_string,
        cost=cost,
        duration=elapsed_time,
        timestamp=start_time,
        retries=0  
    )
    
    return api_call
