import telebot
import requests
import os
from collections import defaultdict

API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not API_TOKEN:
    raise ValueError("Не задана переменная окружения TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(API_TOKEN)
user_contexts = defaultdict(list)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🤖 Привет! Я ваш Telegram бот с поддержкой контекста.\n\n"
        "Доступные команды:\n"
        "/start - вывод всех доступных команд\n"
        "/model - выводит название используемой языковой модели\n"
        "/clear - очистить историю диалога\n\n"
        "Отправьте любое сообщение, и я отвечу с помощью LLM модели, помня наш предыдущий разговор."
    )
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=['model'])
def send_model_name(message):
    try:
        response = requests.get('http://localhost:1234/v1/models')
        
        if response.status_code == 200:
            model_info = response.json()
            model_name = model_info['data'][0]['id']
            bot.reply_to(message, f"🔄 Используемая модель: {model_name}")
        else:
            bot.reply_to(message, '❌ Не удалось получить информацию о модели.')
    except Exception as e:
        bot.reply_to(message, f'❌ Ошибка подключения к LM Studio: {str(e)}')


@bot.message_handler(commands=['clear'])
def clear_context(message):
    user_id = message.from_user.id
    user_contexts[user_id] = []
    bot.reply_to(message, "🗑️ История диалога очищена! Начинаем новый разговор.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_query = message.text
    
    if user_id not in user_contexts:
        user_contexts[user_id] = []
    
    user_contexts[user_id].append({
        "role": "user",
        "content": user_query
    })
    
    request_data = {
        "messages": user_contexts[user_id],
        "temperature": 0.7,
        "max_tokens": 512,
        "stream": False
    }
    
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        response = requests.post(
            'http://localhost:1234/v1/chat/completions',
            json=request_data,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        if response.status_code == 200:
            response_data = response.json()
            assistant_reply = response_data['choices'][0]['message']['content']
            
            user_contexts[user_id].append({
                "role": "assistant", 
                "content": assistant_reply
            })
            
            if len(user_contexts[user_id]) > 20:
                user_contexts[user_id] = user_contexts[user_id][-20:]
            
            bot.reply_to(message, assistant_reply)
        else:
            error_msg = f'❌ Ошибка LM Studio: {response.status_code}'
            bot.reply_to(message, error_msg)
            
    except requests.exceptions.ConnectionError:
        bot.reply_to(message, "❌ Не удалось подключиться к LM Studio. Убедитесь, что сервер запущен на localhost:1234")
    except requests.exceptions.Timeout:
        bot.reply_to(message, "⏰ Таймаут запроса к модели. Попробуйте еще раз.")
    except Exception as e:
        bot.reply_to(message, f'❌ Произошла ошибка: {str(e)}')


if __name__ == '__main__':
    print("🤖 Бот запущен...")
    print("📚 Система контекста активирована")
    print("🔗 Ожидание подключения к LM Studio...")
    bot.polling(none_stop=True)