import os
from dotenv import load_dotenv
import requests
import re
import json
import google.generativeai as genai
import argparse
import sys

# Try to import the new Client-style API
try:
    from google import genai as genai_client
    HAVE_CLIENT_API = True
except ImportError:
    genai_client = None
    HAVE_CLIENT_API = False

# 載入環境變數
load_dotenv()

# 設定Google Form URL
URL = 'https://docs.google.com/forms/d/e/1FAIpQLScuPmKJ0tP8_3bXYRsXbtITNXPJ3rON4RK99u8C9nWCm6-rlA/viewform'

# 設定提示詞
PROMPT_PARTS = [
    "You are a form-filling assistant. Fill out the following form questions with realistic, reasonable answers.",
    "Instructions:",
    "- For multiple choice questions, select ONE option from the provided choices",
    "- For linear scale questions (1-10), pick a number in the middle range (e.g., 5-7)",
    "- For short answer questions, provide brief, realistic responses (e.g., numbers like '3', '20', '7' for count/hour questions)",
    "- Answer ALL questions in order",
    "- Return answers as a JSON array in the EXACT same order as the questions",
    "- Use empty string \"\" only if a question is optional and you cannot provide an answer",
    "- Do NOT use null or None - use actual values",
    "- For date format use: {\"year\": YYYY, \"month\": MM, \"day\": DD}",
    "- For time format use: {\"hour\": HH, \"minute\": MM}",
    "",
    "Example responses:",
    "- For 'How many movies?': \"5\"",
    "- For 'Hours per week?': \"20\"",
    "- For 'Favorite item?' with options ['A', 'B', 'C']: \"B\"",
    "- For scale 1-10: \"7\"",
]

SECTION_TYPE = ["簡答","詳答","選擇題","下拉式選單","核取方塊","線性刻度","標題","單選方格/核取方格","區段","日期","時間","圖片","12","檔案"]
REQUIRED_TYPE = ["非必填","必填"]
SELECTION_TYPE = ["單選方格","核取方格"]

# 字串轉題目列表
def string_to_object_list(js_constant):
    array = json.loads(js_constant)

    objects = []
    for section in array[1][1]:
        if section[4]:
            type = section[3]
            object = {
                'title': section[1],
                'type': type,
            }
            question_list = []
            for tmpe_section in section[4]:
                question = {}
                tmpe_question = tmpe_section
                question['entry_id'] = tmpe_question[0]
                question['required'] = tmpe_question[2]

                if type == 2 or type == 3 or type == 4:
                    question['options'] = [sub_array[0] for sub_array in tmpe_question[1]]
                elif type == 5:
                    question['options'] = [sub_array[0] for sub_array in tmpe_question[1]]
                    question['min'] = tmpe_question[3][0]
                    question['max'] = tmpe_question[3][1]
                elif type == 7:
                    question['selection_type'] = tmpe_question[11][0]
                    question['columns'] = tmpe_question[3][0]
                    question['options'] = [sub_array[0] for sub_array in tmpe_question[1]]
                    
                question_list.append(question)

            object['questions'] = question_list
            objects.append(object)
            
            # print(section)
            # print(object)
            # print()
    return objects

# 題目列表 轉 作答參數
def objects_to_result_strings(url, objects):
    result_strings = []
    for ob in objects:
        for question in ob['questions']:
            if ob['type'] == 9:
                value_object = question['value']
                if 'year' in value_object and value_object['year']:
                    result_strings.append(f"entry.{question['entry_id']}_year={value_object['year']}")
                if 'month' in value_object and value_object['month']:
                    result_strings.append(f"entry.{question['entry_id']}_month={value_object['month']}")
                if 'day' in value_object and value_object['day']:
                    result_strings.append(f"entry.{question['entry_id']}_day={value_object['day']}")
            elif ob['type'] == 10:
                value_object = question['value']
                if 'hour' in value_object and value_object['hour']:
                    result_strings.append(f"entry.{question['entry_id']}_hour={value_object['hour']}")
                if 'minute' in value_object and value_object['minute']:
                    result_strings.append(f"entry.{question['entry_id']}_minute={value_object['minute']}")
            else:
                if 'value' in question and question['value']:
                    if type(question['value']) == list:
                        for value in question['value']:
                            result_strings.append(f"entry.{question['entry_id']}={value}")
                    else:
                        result_strings.append(f"entry.{question['entry_id']}={question['value']}")

    result = "&".join(result_strings)
    result = url + "?"+result
    return result

# 把物件變成文字問題，方便去問AI
def objects_to_string(objects):
    """Convert parsed form objects into a human-readable string for the AI prompt.

    Accepts None or empty list and returns an empty string in that case to avoid
    TypeError when no form was parsed.
    """
    if not objects:
        return ""

    string_list = []
    for ob in objects:
        type = ob['type']
        for question in ob['questions']:
            text = f"問題:{ob['title']}"
            text += f"\n類型:{SECTION_TYPE[ob['type']]}"
            text += f"\n是否必填:{REQUIRED_TYPE[question['required']]}"

            if type == 2 or type == 3 or type == 4:
                text += f"\n選項:{question.get('options')}"
            elif type == 5:
                text += f"\n選項:{question.get('options')}"
                text += f"\n最小為:{question.get('min')}"
                text += f"\n最大為:{question.get('max')}"
            elif type == 7:
                text += f"\n題目:{question.get('columns')}"
                text += f"\n選項類型:{SELECTION_TYPE[question.get('selection_type', 0)]}"
                text += f"\n選項:{question.get('options')}"
            string_list.append(text)
    return "\n\n".join(string_list)
            

# 陣列作答題目
def set_answer(topic_list, answer_list):
    for ob in topic_list:
        for question in ob['questions']:
            answer = answer_list.pop(0)
            question['value'] = answer


# 獲取Google Form
def get_form(url):
    response = requests.get(url)

    # 检查是否成功获取网页内容
    if response.status_code == 200:
        # 使用正则表达式提取JS常量
        js_constants = re.findall(r'FB_PUBLIC_LOAD_DATA_.*?=(.*?);', response.text)

        if js_constants:
            # 输出提取到的JS常量
            for js_constant in js_constants:
                list = string_to_object_list(js_constant)
                return list
        else:
            print("No FB_PUBLIC_LOAD_DATA_ JS constants found on the page.")
    else:
        print("Failed to retrieve the webpage. Status code:", response.status_code)


def main():
    # 從環境變數獲取API金鑰
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("未設定GEMINI_API_KEY環境變數")

    # CLI: allow overriding the URL and model name
    parser = argparse.ArgumentParser(description='Auto fill Google Forms via AI')
    parser.add_argument('--form-url', dest='form_url', help='Google Form URL to process', required=False)
    parser.add_argument('--model-name', dest='model_name', help='Generative model name', 
                        required=False, default=os.getenv('MODEL_NAME', 'gemini-2.0-flash-exp'))
    args = parser.parse_args()

    target_url = args.form_url if args.form_url else URL

    form = get_form(target_url)
    if not form:
        print(f"Error: failed to fetch or parse the Google Form at: {target_url}")
        sys.exit(2)

    form_string = objects_to_string(form)

    # 將form_string添加到prompt_parts
    prompt_parts = PROMPT_PARTS + [form_string + "\n用陣列JSON格式回答所有問題"]

    print("\n" + form_string + "\n")
    
    # Try using the new Client API first, fallback to old API if needed
    model_name = args.model_name
    response_text = None
    
    try:
        if HAVE_CLIENT_API:
            # Use new google.genai Client API
            client = genai_client.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_parts
            )
            response_text = response.text
        else:
            # Fallback to old google.generativeai API
            genai.configure(api_key=api_key)
            
            generation_config = {
                "temperature": 0.9,
                "top_p": 1,
                "top_k": 1,
                "max_output_tokens": 2048,
            }
            
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
            ]
            
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            response = model.generate_content(prompt_parts)
            response_text = response.text
    except Exception as e:
        print(f"Error generating content with model '{model_name}': {e}")
        print("Tip: Make sure you have the correct model name and API access.")
        sys.exit(3)
    
    if not response_text:
        print("No text returned from model response.")
        sys.exit(4)
    
    print(response_text)
    
    # Extract JSON from response text (handle markdown code fences)
    json_text = response_text.strip()
    if json_text.startswith("```json"):
        # Remove markdown code fences
        json_text = json_text[7:]  # Remove ```json
        if json_text.endswith("```"):
            json_text = json_text[:-3]  # Remove ```
        json_text = json_text.strip()
    elif json_text.startswith("```"):
        # Remove generic code fences
        json_text = json_text[3:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]
        json_text = json_text.strip()
    
    try:
        parsed_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response text: {json_text}")
        sys.exit(5)
    
    set_answer(form, parsed_data)
    print("Google Form自動填寫網址：\n" + objects_to_result_strings(target_url, form))

if __name__ == "__main__":
    main()