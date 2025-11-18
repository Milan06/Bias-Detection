from openai import OpenAI
import base64
from pdfminer.high_level import extract_pages, extract_text
from dotenv import load_dotenv
import os
import fitz  #PyMuPDF
import PIL.Image #pillow
import io


#image extractor 
pdf = fitz.open("videogame.pdf")
counter = 1
for i in range(len(pdf)):
    page = pdf[i]
    images = page.get_images()
    for image in images:
        base_img = pdf.extract_image(image[0])
        image_data = base_img["image"]
        img = PIL.Image.open(io.BytesIO(image_data))
        extension = base_img["ext"]
        img.save(open(f"image{counter}.{extension}", "wb"))
        counter += 1 


#extracts a pdf into a txt format to be translated into a string for gpt to read
text = extract_text("videogame.pdf")

file = open("article.txt", "w")

file.writelines(text) 

load_dotenv()

#API Key
client = OpenAI ()

#Reading txt to a string
with open("article.txt", "r") as file:
    lines = file.readlines()
    file_content = ''.join(lines)

#Detects all bias points needed to be found and analyses them in list/paragraph format
def biasPoints(files):
    findBiasPrompt = "Define core bias detection categories, Narrative bias (storyline framing), Sentiment bias (positive/negative choice of words), Regional bias (geographic over/underrepresentation), Slant (partisan word usage or source citations) and Coverage depth (Single-source vs multi-source reporting), within this article" + files


    chat1 = client.chat.completions.create (
        messages = [
            {
                "role":"user",
                "content": findBiasPrompt,
            }       
        ],
        model="gpt-4o-mini",
        max_tokens = 650
    )

    printBias = chat1.choices[0].message.content
    return printBias

#gives a score for the overall severity of the bias found
def biasScore(analysis):
    giveBiasScorePrompt = "Based off this output give an overall scoring out of 10 (1 being not severe at all), for the severity of the bias detected with a short summary of why you got that score, this is the analysis" + analysis + "this is the content from the article" + file_content
    chat2 = client.chat.completions.create (
        messages = [
            {
                "role":"user",
                "content": giveBiasScorePrompt,
            }
        ],
        model="gpt-4o-mini",
        max_tokens = 600
    )

    printScore = chat2.choices[0].message.content
    return printScore

#Highlights trigger phrases 
def triggerphrases(textfile, analysis):
    triggerPhrasePrompt = "Identify a list of 3 trigger phrases further support the analysis" + analysis + "within the text" +  textfile
    chat3 = client.chat.completions.create (
        messages = [
            {
                "role":"user",
                "content": triggerPhrasePrompt,
            }
        ],
        model="gpt-4o-mini",
        max_tokens = 200
    )
    printTriggerPhrases = chat3.choices[0].message.content
    return printTriggerPhrases

#reads generated image

def replace_char(s, index, char):
  return s[:index] + char + s[index+1:]

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')
  






#--------------------------
#       main program
#--------------------------

print("")

biasAnalysis = biasPoints(file_content)
print(biasAnalysis)
print(biasScore(biasAnalysis))
print(triggerphrases(file_content, biasAnalysis))

number_jpeg = 2
number_png = 2

my_string_jpeg = "image1.jpeg"
my_string_png = "image1.png"

for i in range(6):
    if os.path.exists(my_string_jpeg):
        base64_image = encode_image(my_string_jpeg)
        response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
            "role": "user",
            "content": [
                {"type": "text", "text": "Breifly describe in 2-3 scentences how this image relates to the bias detected throughout the article."},
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
                }
            ]
            }
        ],
        max_tokens=300,
        )
        print(my_string_jpeg + ": " + response.choices[0].message.content)

    string_representation_jpeg = str(number_jpeg)
    my_string_jpeg = replace_char(my_string_jpeg, 5, string_representation_jpeg)
    number_jpeg = number_jpeg + 1

    if os.path.exists(my_string_png):
        base64_image = encode_image(my_string_png)
        response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
            "role": "user",
            "content": [
                {"type": "text", "text": "Breifly describe in 2-3 scentences how this image relates to the bias detected throughout the article."},
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
                }
            ]
            }
        ],
        max_tokens=300,
        )   
        print(my_string_png + ": " + response.choices[0].message.content)

    string_representation_png = str(number_png)
    my_string_png = replace_char(my_string_png, 5, string_representation_png)
    number_png = number_png + 1






