import os
import random
import threading
import time
from flask import Flask
import telebot
from telebot import types

# ----------------- कॉन्फ़िगरेशन -----------------
TOKEN = '8818399396:AAGz1-xkSUprQUr8ST64AoC_ire81rObcEU'  # आपका बोट टोकन
ADMIN_ID = 6262854630  # आपकी Telegram User ID
ADMIN_USERNAME = 'Helpbot655_bot'  # आपका टेलीग्राम यूज़रनेम (बिना @ के)
REQUIRED_CHANNEL = '@ksp008h'  # आपका टेलीग्राम चैनल यूजरनेम
# ------------------------------------------------

bot = telebot.TeleBot(TOKEN)

# डेटाबेस (Memory Storage)
users = {}
user_state = {}
temp_promotion_data = {}
pending_approvals = {}  # एडमिन अप्रूवल के लिए पेंडिंग स्क्रीनशॉट

# डायनामिक सेटिंग्स
bot_settings = {
    'reward_coins': 10,
    'cost_per_hour': 20,  # प्रति घंटे का चार्ज
    'daily_bonus': 50,  # डेली बोनस कॉइन्स
    'referral_bonus': 15,  # रेफरल बोनस
}

ig_follow_pool = []
ig_like_pool = []
yt_sub_pool = []


# ----------------- ऑटो-क्लीनअप बैकग्राउंड वर्कर -----------------
def cleanup_expired_promotions():
  while True:
    current_time = time.time()
    global ig_follow_pool, ig_like_pool, yt_sub_pool
    ig_follow_pool = [
        item for item in ig_follow_pool if item['expires_at'] > current_time
    ]
    ig_like_pool = [
        item for item in ig_like_pool if item['expires_at'] > current_time
    ]
    yt_sub_pool = [
        item for item in yt_sub_pool if item['expires_at'] > current_time
    ]
    time.sleep(60)


threading.Thread(target=cleanup_expired_promotions, daemon=True).start()


# ----------------- चैनल मेंबरशिप चेक फंक्शन -----------------
def check_subscription(user_id):
  try:
    member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
    if member.status in ['member', 'administrator', 'creator']:
      return True
  except Exception as e:
    print(f'Error checking subscription: {e}')
  return False


# ----------------- कीबोर्ड जनरेटर -----------------
def get_main_menu(user_id):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      types.KeyboardButton('📸 IG Follow Tasks'),
      types.KeyboardButton('❤️ IG Like Tasks'),
  )
  markup.add(
      types.KeyboardButton('▶️ YT Sub Tasks'),
      types.KeyboardButton('➕ Promote Link'),
  )
  markup.add(
      types.KeyboardButton('🎁 Daily Bonus'),
      types.KeyboardButton('👥 Invite & Earn (Referral)'),
  )
  markup.add(
      types.KeyboardButton('💰 My Profile'),
      types.KeyboardButton('💳 Buy Coins (Premium)'),
  )
  markup.add(types.KeyboardButton('🎧 Support / Help'))

  if user_id == ADMIN_ID:
    markup.add(types.KeyboardButton('👑 Admin Panel'))

  return markup


def get_admin_menu():
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(types.KeyboardButton('🔔 Pending Task Approvals'))
  markup.add(
      types.KeyboardButton('⚙️ Set Reward Coins'),
      types.KeyboardButton('⚙️ Set Cost Per Hour'),
  )
  markup.add(
      types.KeyboardButton('⚙️ Set Daily Bonus'),
      types.KeyboardButton('⚙️ Set Referral Bonus'),
  )
  markup.add(types.KeyboardButton('➕ Add Coins to User'))
  markup.add(types.KeyboardButton('🏠 Back to Main Menu'))
  return markup


# ----------------- स्टार्ट कमांड -----------------
@bot.message_handler(commands=['start'])
def start_bot(message):
  user_id = message.from_user.id
  user_state[user_id] = None

  args = message.text.split()
  referrer_id = None
  if len(args) > 1:
    try:
      referrer_id = int(args[1])
    except ValueError:
      pass

  if not check_subscription(user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            '📢 Join Channel',
            url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}",
        )
    )

    cb_data = f'check_sub_{referrer_id}' if referrer_id else 'check_sub_0'
    markup.add(
        types.InlineKeyboardButton(
            '🔄 Check Membership', callback_data=cb_data
        )
    )

    bot.send_message(
        message.chat.id,
        '❌ **बोट का उपयोग करने के लिए आपको हमारा चैनल ज्वॉइन करना अनिवार्य'
        ' है!**\n\n'
        f'पहले नीचे दिए गए बटन पर क्लिक करके हमारा चैनल ज्वॉइन करें: 👉'
        f' {REQUIRED_CHANNEL}\n\n'
        'चैनल ज्वॉइन करने के बाद **\'Check Membership\'** बटन पर क्लिक करें।',
        parse_mode='Markdown',
        reply_markup=markup,
    )
    return

  if user_id not in users:
    users[user_id] = {
        'balance': 0,
        'promotions': [],
        'last_bonus_time': 0,
        'completed_tasks': [],
        'referred_by': None,
        'referral_count': 0,
    }

    if referrer_id and referrer_id in users and referrer_id != user_id:
      users[user_id]['referred_by'] = referrer_id
      users[referrer_id]['referral_count'] = (
          users[referrer_id].get('referral_count', 0) + 1
      )
      users[referrer_id]['balance'] += bot_settings['referral_bonus']
      try:
        bot.send_message(
            referrer_id,
            '🎉 **नया रेफरल!**\nआपके लिंक से एक यूजर ने बोट जॉइन किया है। आपको'
            f" **+{bot_settings['referral_bonus']} Coins** मिले हैं!",
            parse_mode='Markdown',
        )
      except:
        pass

  welcome_text = (
      '👋 **Multi-Promote Bot में आपका स्वागत है!**\n\n'
      'यहाँ आप टास्क पूरे करके कॉइन्स कमा सकते हैं और अपने लिंक्स को घंटों के'
      ' हिसाब से प्रमोट कर सकते हैं।\n\n'
      '👇 नीचे दिए गए मेनू से विकल्प चुनें:'
  )
  bot.send_message(
      message.chat.id,
      welcome_text,
      parse_mode='Markdown',
      reply_markup=get_main_menu(user_id),
  )


# ----------------- फोटो/स्क्रीनशॉट हैंडलर -----------------
@bot.message_handler(content_types=['photo'])
def handle_photos(message):
  user_id = message.from_user.id
  if user_state.get(user_id) == 'WAITING_SCREENSHOT':
    target_val = user_state.get(f'target_{user_id}')
    user_state[user_id] = None

    photo_id = message.photo[-1].file_id

    req_id = f'req_{user_id}_{int(time.time())}'
    pending_approvals[req_id] = {
        'user_id': user_id,
        'username': message.from_user.username or message.from_user.first_name,
        'reward': bot_settings['reward_coins'],
        'target': target_val,
    }

    bot.send_message(
        message.chat.id,
        '⏳ **आपका स्क्रीनशॉट एडमिन के पास वेरिफिकेशन के लिए भेज दिया गया'
        ' है!**\n\n'
        'कृपया **10 से 15 मिनट** प्रतीक्षा करें। एडमिन द्वारा चेक करने के बाद'
        ' आपके कॉइन्स जोड़ दिए जाएंगे।',
        parse_mode='Markdown',
        reply_markup=get_main_menu(user_id),
    )

    admin_markup = types.InlineKeyboardMarkup(row_width=2)
    admin_markup.add(
        types.InlineKeyboardButton('✅ Approve', callback_data=f'app_{req_id}'),
        types.InlineKeyboardButton('❌ Reject', callback_data=f'rej_{req_id}'),
    )

    bot.send_photo(
        ADMIN_ID,
        photo_id,
        caption=(
            '🔔 **नया टास्क स्क्रीनशॉट आया है!**\n\n'
            f"👤 यूजर: @{message.from_user.username or 'No Username'} (ID:"
            f' `{user_id}`)\n'
            f'🎯 टारगेट: `{target_val}`\n'
            f"🎁 रिवॉर्ड: `{bot_settings['reward_coins']} Coins`"
        ),
        parse_mode='Markdown',
        reply_markup=admin_markup,
    )
  else:
    bot.send_message(
        message.chat.id,
        '❌ कृपया पहले कोई टास्क चुनें और नियमों के अनुसार आगे बढ़ें।',
    )


# ----------------- टेक्स्ट और स्टेट हैंडलर -----------------
@bot.message_handler(func=lambda message: True)
def handle_text(message):
  user_id = message.from_user.id
  text = message.text

  if not check_subscription(user_id):
    return

  if user_id not in users:
    users[user_id] = {
        'balance': 0,
        'promotions': [],
        'last_bonus_time': 0,
        'completed_tasks': [],
        'referred_by': None,
        'referral_count': 0,
    }

  current_state = user_state.get(user_id)

  # 1. प्रमोट इनपुट स्टेट्स
  if current_state in [
      'WAITING_IG_FOLLOW',
      'WAITING_IG_LIKE',
      'WAITING_YT_SUB',
  ]:
    entry = text.strip()

    if current_state == 'WAITING_IG_FOLLOW':
      entry = entry.strip().lstrip('@')
      if 'instagram.com' in entry:
        entry = (
            entry.split('instagram.com/')[-1]
            .split('/')[0]
            .split('?')[0]
            .replace('@', '')
        )

    temp_promotion_data[user_id] = {'type': current_state, 'target': entry}
    user_state[user_id] = 'WAITING_HOURS'

    cost_1h = bot_settings['cost_per_hour']
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton('1 घंटा', callback_data='hrs_1'),
        types.InlineKeyboardButton('3 घंटे', callback_data='hrs_3'),
        types.InlineKeyboardButton('6 घंटे', callback_data='hrs_6'),
        types.InlineKeyboardButton('12 घंटे', callback_data='hrs_12'),
        types.InlineKeyboardButton('24 घंटे', callback_data='hrs_24'),
    )
    bot.send_message(
        message.chat.id,
        f'⏱️ **यूजरनेम/लिंक दर्ज हो गया:** `{entry}`\n\n'
        f'इसे कितने समय के लिए लाइव रखना चाहते हैं?\n'
        f'रेट: `{cost_1h} Coins` प्रति घंटा',
        parse_mode='Markdown',
        reply_markup=markup,
    )
    return

  # 2. एडमिन पैनल स्टेट्स
  if user_id == ADMIN_ID and current_state in [
      'SET_REWARD',
      'SET_COST',
      'SET_BONUS',
      'SET_REFERRAL',
      'ADD_COINS_INPUT',
  ]:
    if current_state == 'SET_REWARD':
      try:
        bot_settings['reward_coins'] = int(text.strip())
        bot.send_message(
            message.chat.id,
            f"✅ अपडेट हो गया! नया रिवॉर्ड: {bot_settings['reward_coins']} Coins",
            reply_markup=get_admin_menu(),
        )
      except ValueError:
        bot.send_message(message.chat.id, '❌ कृपया सिर्फ नंबर भेजें।')
      user_state[user_id] = None
      return

    elif current_state == 'SET_COST':
      try:
        bot_settings['cost_per_hour'] = int(text.strip())
        bot.send_message(
            message.chat.id,
            f"✅ अपडेट हो गया! नई कीमत: {bot_settings['cost_per_hour']} Coins",
            reply_markup=get_admin_menu(),
        )
      except ValueError:
        bot.send_message(message.chat.id, '❌ कृपया सिर्फ नंबर भेजें।')
      user_state[user_id] = None
      return

    elif current_state == 'SET_BONUS':
      try:
        bot_settings['daily_bonus'] = int(text.strip())
        bot.send_message(
            message.chat.id,
            f"✅ अपडेट हो गया! नया डेली बोनस: {bot_settings['daily_bonus']} Coins",
            reply_markup=get_admin_menu(),
        )
      except ValueError:
        bot.send_message(message.chat.id, '❌ कृपया सिर्फ नंबर भेजें।')
      user_state[user_id] = None
      return

    elif current_state == 'SET_REFERRAL':
      try:
        bot_settings['referral_bonus'] = int(text.strip())
        bot.send_message(
            message.chat.id,
            f"✅ अपडेट हो गया! नया रेफरल बोनस:"
            f" {bot_settings['referral_bonus']} Coins",
            reply_markup=get_admin_menu(),
        )
      except ValueError:
        bot.send_message(message.chat.id, '❌ कृपया सिर्फ नंबर भेजें।')
      user_state[user_id] = None
      return

    elif current_state == 'ADD_COINS_INPUT':
      try:
        parts = text.strip().split()
        if len(parts) == 2:
          target_user_id = int(parts[0])
          coins_to_add = int(parts[1])
          if target_user_id not in users:
            users[target_user_id] = {
                'balance': 0,
                'promotions': [],
                'last_bonus_time': 0,
                'completed_tasks': [],
                'referred_by': None,
                'referral_count': 0,
            }
          users[target_user_id]['balance'] += coins_to_add
          bot.send_message(
              message.chat.id,
              '✅ सफलतापूर्वक कॉइन जोड़ दिए गए!',
              reply_markup=get_admin_menu(),
          )
        else:
          bot.send_message(
              message.chat.id,
              '❌ गलत फॉर्मेट! उदाहरण दें: `123456 500`',
              parse_mode='Markdown',
          )
      except Exception as e:
        bot.send_message(message.chat.id, f'❌ एरर: {e}')
      user_state[user_id] = None
      return

  # 3. एडमिन पैनल बटन क्लिक्स
  if text == '👑 Admin Panel' and user_id == ADMIN_ID:
    user_state[user_id] = None
    bot.send_message(
        message.chat.id,
        f'👑 **Welcome to Admin Panel**\n\nCurrent Reward:'
        f" `{bot_settings['reward_coins']}`\nCost Per Hour:"
        f" `{bot_settings['cost_per_hour']}`\nDaily Bonus:"
        f" `{bot_settings['daily_bonus']}`\nReferral Bonus:"
        f" `{bot_settings['referral_bonus']}`",
        reply_markup=get_admin_menu(),
        parse_mode='Markdown',
    )
    return

  elif text == '🔔 Pending Task Approvals' and user_id == ADMIN_ID:
    if not pending_approvals:
      bot.send_message(
          message.chat.id, '📭 अभी कोई भी पेंडिंग स्क्रीनशॉट अप्रूवल के लिए नहीं है।'
      )
    else:
      bot.send_message(
          message.chat.id,
          f'📋 कुल पेंडिंग रिक्वेस्ट्स: `{len(pending_approvals)}`',
          parse_mode='Markdown',
      )
    return

  elif text == '🏠 Back to Main Menu' and user_id == ADMIN_ID:
    user_state[user_id] = None
    bot.send_message(
        message.chat.id,
        '🏠 Main Menu में वापसी:',
        reply_markup=get_main_menu(user_id),
    )
    return

  elif text == '⚙️ Set Reward Coins' and user_id == ADMIN_ID:
    user_state[user_id] = 'SET_REWARD'
    bot.send_message(
        message.chat.id, 'नया टास्क रिवॉर्ड अमाउंट टाइप करके भेजें (सिर्फ नंबर):'
    )
    return

  elif text == '⚙️ Set Cost Per Hour' and user_id == ADMIN_ID:
    user_state[user_id] = 'SET_COST'
    bot.send_message(
        message.chat.id,
        'प्रमोशन की प्रति घंटे की कीमत टाइप करके भेजें (सिर्फ नंबर):',
    )
    return

  elif text == '⚙️ Set Daily Bonus' and user_id == ADMIN_ID:
    user_state[user_id] = 'SET_BONUS'
    bot.send_message(
        message.chat.id,
        'नया डेली बोनस कॉइन अमाउंट टाइप करके भेजें (सिर्फ नंबर):',
    )
    return

  elif text == '⚙️ Set Referral Bonus' and user_id == ADMIN_ID:
    user_state[user_id] = 'SET_REFERRAL'
    bot.send_message(
        message.chat.id,
        'नया रेफरल बोनस कॉइन अमाउंट टाइप करके भेजें (सिर्फ नंबर):',
    )
    return

  elif text == '➕ Add Coins to User' and user_id == ADMIN_ID:
    user_state[user_id] = 'ADD_COINS_INPUT'
    bot.send_message(
        message.chat.id,
        '➕ सही फॉर्मेट में भेजें:\n`User_ID Space Coins`\nउदाहरण: `123456 500`',
        parse_mode='Markdown',
    )
    return

  # 4. मुख्य मेनू (Main Menu Buttons)
  if text == '🎁 Daily Bonus':
    current_time = time.time()
    last_bonus_time = users[user_id].get('last_bonus_time', 0)
    cooldown = 86400

    if current_time - last_bonus_time < cooldown:
      remaining_time = int(cooldown - (current_time - last_bonus_time))
      hours = remaining_time // 3600
      minutes = (remaining_time % 3600) // 60
      bot.send_message(
          message.chat.id,
          '⏳ आप आज का बोनस पहले ही ले चुके हैं!\nअगला बोनस आपको **'
          f' {hours} घंटे {minutes} मिनट** बाद मिलेगा।',
          parse_mode='Markdown',
      )
    else:
      bonus_amt = bot_settings['daily_bonus']
      users[user_id]['balance'] += bonus_amt
      users[user_id]['last_bonus_time'] = current_time
      bot.send_message(
          message.chat.id,
          '🎉 बधाई हो! आपको सफलतापूर्वक'
          f' **+{bonus_amt} Coins** डेली बोनस मिल गया है!',
          parse_mode='Markdown',
          reply_markup=get_main_menu(user_id),
      )

  elif text == '👥 Invite & Earn (Referral)':
    bot_info = bot.get_me()
    bot_username = bot_info.username
    referral_link = f'https://t.me/{bot_username}?start={user_id}'

    ref_count = users[user_id].get('referral_count', 0)
    bonus = bot_settings['referral_bonus']

    msg = (
        f'👥 **Refer & Earn Program**\n\n'
        f'अपने दोस्तों को आमंत्रित करें और प्रत्येक सफल रेफ़रल पर **{bonus}'
        ' Coins** कमाएं!\n\n'
        f'🔗 **आपका रेफरल लिंक:**\n`{referral_link}`\n\n'
        f'📊 **आपके कुल इनवाइट्स:** `{ref_count}`\n\n'
        '⚠️ *नोट: पॉइंट्स तभी मिलेंगे जब आपका दोस्त बोट स्टार्ट करके हमारा चैनल'
        ' ज्वॉइन करेगा।*'
    )
    markup = types.InlineKeyboardMarkup()
    share_url = (
        'https://t.me/share/url?url='
        + referral_link
        + '&text=🌟%20इस%20बोट%20से%20पॉइंट्स%20कमाएं%20और%20प्रमोशन%20करें!'
    )
    markup.add(
        types.InlineKeyboardButton('📤 दोस्तों को शेयर करें', url=share_url)
    )

    bot.send_message(
        message.chat.id, msg, parse_mode='Markdown', reply_markup=markup
    )

  elif text == '💳 Buy Coins (Premium)':
    bot.send_message(
        message.chat.id,
        '💎 कॉइन्स खरीदने के लिए Support पर संपर्क करें।',
        parse_mode='Markdown',
    )

  elif text == '🎧 Support / Help':
    support_markup = types.InlineKeyboardMarkup()
    support_markup.add(
        types.InlineKeyboardButton(
            '💬 Contact Admin', url=f'https://t.me/{ADMIN_USERNAME}'
        )
    )
    bot.send_message(
        message.chat.id,
        f'📞 **Customer Support**\n👤 Admin: `@{ADMIN_USERNAME}`',
        parse_mode='Markdown',
        reply_markup=support_markup,
    )

  elif text == '💰 My Profile':
    bal = users[user_id]['balance']
    promos = len(users[user_id]['promotions'])
    ref_count = users[user_id].get('referral_count', 0)
    bot.send_message(
        message.chat.id,
        f'👤 **Your Profile**\n\n🆔 User ID: `{user_id}`\n💰 Balance: `{bal}`\n👥'
        f' Referrals: `{ref_count}`\n🚀 Promotions: `{promos}`',
        parse_mode='Markdown',
    )

  elif text == '📸 IG Follow Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [
        item for item in ig_follow_pool if item['target'] not in completed
    ]

    if len(available_pool) == 0:
      bot.send_message(
          message.chat.id,
          '❌ आपके लिए अभी कोई नया IG फॉलो टास्क उपलब्ध नहीं है। सभी टास्क'
          ' पूरे हो चुके हैं!',
      )
      return

    item = random.choice(available_pool)
    user_state[f'temp_target_{user_id}'] = item['target']

    target_val = item['target']
    if target_val.startswith('http'):
      profile_url = target_val
    else:
      profile_url = f'https://instagram.com/{target_val}'

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🔗 Follow Profile', url=profile_url))
    markup.add(
        types.InlineKeyboardButton(
            '✅ Task Complete किया (स्क्रीनशॉट भेजें)',
            callback_data='ask_screenshot',
        )
    )
    bot.send_message(
        message.chat.id,
        f'📌 **इस नए अकाउंट को फॉलो करें:**\n👉 `{target_val}`\n\nफॉलो करने के'
        ' बाद नीचे दिए गए बटन पर क्लिक करके **स्क्रीनशॉट** भेजें।',
        reply_markup=markup,
        parse_mode='Markdown',
    )

  elif text == '❤️ IG Like Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [
        item for item in ig_like_pool if item['target'] not in completed
    ]

    if len(available_pool) == 0:
      bot.send_message(
          message.chat.id,
          '❌ आपके लिए अभी कोई नया IG लाइक टास्क उपलब्ध नहीं है।',
      )
      return

    item = random.choice(available_pool)
    user_state[f'temp_target_{user_id}'] = item['target']

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('❤️ Like Post', url=item['target']))
    markup.add(
        types.InlineKeyboardButton(
            '✅ Task Complete किया (स्क्रीनशॉट भेजें)',
            callback_data='ask_screenshot',
        )
    )
    bot.send_message(
        message.chat.id,
        '📌 **इस नई पोस्ट को लाइक करें और स्क्रीनशॉट भेजें:**',
        reply_markup=markup,
        parse_mode='Markdown',
    )

  elif text == '▶️ YT Sub Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [
        item for item in yt_sub_pool if item['target'] not in completed
    ]

    if len(available_pool) == 0:
      bot.send_message(
          message.chat.id,
          '❌ आपके लिए अभी कोई नया YouTube टास्क उपलब्ध नहीं है।',
      )
      return

    item = random.choice(available_pool)
    user_state[f'temp_target_{user_id}'] = item['target']

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('▶️ Subscribe Channel', url=item['target'])
    )
    markup.add(
        types.InlineKeyboardButton(
            '✅ Task Complete किया (स्क्रीनशॉट भेजें)',
            callback_data='ask_screenshot',
        )
    )
    bot.send_message(
        message.chat.id,
        '📌 **इस नए चैनल को सब्सक्राइब करें और स्क्रीनशॉट भेजें:**',
        reply_markup=markup,
        parse_mode='Markdown',
    )

  elif text == '➕ Promote Link':
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            '📸 IG Follow (Username)', callback_data='add_ig_follow'
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            '❤️ IG Like/Reel (Post Link)', callback_data='add_ig_like'
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            '▶️ YT Sub (Channel Link)', callback_data='add_yt_sub'
        )
    )
    bot.send_message(
        message.chat.id,
        '🚀 आप क्या प्रमोट करना चाहते हैं?',
        reply_markup=markup,
        parse_mode='Markdown',
    )

  else:
    bot.send_message(
        message.chat.id, '❌ कृपया नीचे दिए गए मेनू विकल्पों का उपयोग करें।'
    )


# ----------------- कॉलबैक हैंडलर -----------------
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
  user_id = call.from_user.id

  if call.data.startswith('check_sub'):
    parts = call.data.split('_')
    referrer_id = int(parts[2]) if len(parts) > 2 else 0

    if check_subscription(user_id):
      bot.answer_callback_query(call.id, '✅ चैनल ज्वॉइन कर लिया गया है!')
      try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
      except:
        pass

      if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'promotions': [],
            'last_bonus_time': 0,
            'completed_tasks': [],
            'referred_by': None,
            'referral_count': 0,
        }

        if referrer_id and referrer_id in users and referrer_id != user_id:
          users[user_id]['referred_by'] = referrer_id
          users[referrer_id]['referral_count'] = (
              users[referrer_id].get('referral_count', 0) + 1
          )
          users[referrer_id]['balance'] += bot_settings['referral_bonus']
          try:
            bot.send_message(
                referrer_id,
                '🎉 **नया रेफरल!**\nआपके लिंक से एक यूजर ने बोट और चैनल जॉइन किया'
                f" है। आपको **+{bot_settings['referral_bonus']} Coins** मिले"
                ' हैं!',
                parse_mode='Markdown',
            )
          except:
            pass

      bot.send_message(
          call.message.chat.id,
          '👋 स्वागत है!',
          reply_markup=get_main_menu(user_id),
      )
    else:
      bot.answer_callback_query(
          call.id,
          '❌ आपने अभी तक चैनल ज्वॉइन नहीं किया है!',
          show_alert=True,
      )

  elif call.data == 'ask_screenshot':
    user_state[user_id] = 'WAITING_SCREENSHOT'
    current_target = user_state.get(f'temp_target_{user_id}')
    user_state[f'target_{user_id}'] = current_target

    bot.answer_callback_query(call.id, 'कृपया स्क्रीनशॉट अपलोड करें!')
    bot.send_message(
        call.message.chat.id,
        '📸 कृपया टास्क पूरा करने का **स्क्रीनशॉट (Screenshot)** फोटो के'
        ' रूप में यहाँ चैट में भेजें।',
    )

  elif call.data.startswith('app_') or call.data.startswith('rej_'):
    if user_id != ADMIN_ID:
      bot.answer_callback_query(
          call.id, '❌ आप एडमिन नहीं हैं!', show_alert=True
      )
      return

    action, req_id = call.data.split('_', 1)

    if req_id not in pending_approvals:
      bot.answer_callback_query(
          call.id,
          '❌ यह रिक्वेस्ट पहले ही प्रोसेस की जा चुकी है!',
          show_alert=True,
      )
      return

    data = pending_approvals.pop(req_id)
    target_user_id = data['user_id']
    reward = data['reward']
    task_target = data['target']

    if target_user_id not in users:
      users[target_user_id] = {
          'balance': 0,
          'promotions': [],
          'last_bonus_time': 0,
          'completed_tasks': [],
          'referred_by': None,
          'referral_count': 0,
      }

    if action == 'app':
      users[target_user_id]['balance'] += reward

      if (
          task_target
          and task_target not in users[target_user_id]['completed_tasks']
      ):
        users[target_user_id]['completed_tasks'].append(task_target)

      bot.answer_callback_query(
          call.id, '✅ अप्रूव कर दिया गया और कॉइन्स जोड़ दिए गए!'
      )
      try:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=(
                f'{call.message.caption}\n\n🟢 **Status: APPROVED (+{reward}'
                ' Coins added)**'
            ),
            parse_mode='Markdown',
        )
      except:
        pass

      try:
        bot.send_message(
            target_user_id,
            '🎉 **बधाई हो! आपका टास्क अप्रूव हो गया है।**\nआपके अकाउंट में'
            f' **+{reward} Coins** जोड़ दिए गए हैं!',
            parse_mode='Markdown',
        )
      except:
        pass

    elif action == 'rej':
      bot.answer_callback_query(
          call.id, '❌ टास्क अस्वीकार (Reject) कर दिया गया!'
      )
      try:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f'{call.message.caption}\n\n🔴 **Status: REJECTED**',
            parse_mode='Markdown',
        )
      except:
        pass

      try:
        bot.send_message(
            target_user_id,
            '❌ **आपका टास्क स्क्रीनशॉट एडमिन द्वारा अस्वीकार (Reject) कर दिया'
            ' गया है।** कृपया सही स्क्रीनशॉट दोबारा भेजें।',
            parse_mode='Markdown',
        )
      except:
        pass

  elif call.data == 'add_ig_follow':
    user_state[user_id] = 'WAITING_IG_FOLLOW'
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        '📸 **अपना Instagram Username या Profile Link भेजें:**\n\n'
        'उदा: `rohit_sharma` या `https://instagram.com/rohit_sharma`',
        parse_mode='Markdown',
    )

  elif call.data == 'add_ig_like':
    user_state[user_id] = 'WAITING_IG_LIKE'
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        '❤️ **अपनी Instagram Post या Reel का पूरा लिंक भेजें:**',
        parse_mode='Markdown',
    )

  elif call.data == 'add_yt_sub':
    user_state[user_id] = 'WAITING_YT_SUB'
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        '▶️ **अपने YouTube Channel का पूरा लिंक भेजें:**',
        parse_mode='Markdown',
    )

  elif call.data.startswith('hrs_'):
    if user_id not in temp_promotion_data:
      bot.answer_callback_query(
          call.id, '❌ कुछ गड़बड़ हो गई!', show_alert=True
      )
      return

    hours = int(call.data.split('_')[1])
    total_cost = hours * bot_settings['cost_per_hour']

    if users[user_id]['balance'] < total_cost:
      bot.answer_callback_query(
          call.id,
          f'❌ अपर्याप्त बैलेंस! {total_cost} Coins चाहिए।',
          show_alert=True,
      )
      user_state[user_id] = None
      temp_promotion_data.pop(user_id, None)
      return

    users[user_id]['balance'] -= total_cost
    promo_info = temp_promotion_data[user_id]
    expires_at = time.time() + (hours * 3600)

    pool_item = {
        'target': promo_info['target'],
        'expires_at': expires_at,
        'owner_id': user_id,
    }

    if promo_info['type'] == 'WAITING_IG_FOLLOW':
      ig_follow_pool.append(pool_item)
    elif promo_info['type'] == 'WAITING_IG_LIKE':
      ig_like_pool.append(pool_item)
    elif promo_info['type'] == 'WAITING_YT_SUB':
      yt_sub_pool.append(pool_item)

    users[user_id]['promotions'].append(pool_item)
    user_state[user_id] = None
    temp_promotion_data.pop(user_id, None)

    try:
      bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
      pass

    bot.send_message(
        call.message.chat.id,
        '✅ **सफलतापूर्वक प्रमोट हो गया!**\nआपके'
        f' `{total_cost} Coins` काट लिए गए हैं।',
        reply_markup=get_main_menu(user_id),
        parse_mode='Markdown',
    )
    bot.answer_callback_query(call.id, 'Promotion Successful!')


# ----------------- FLASK KEEPALIVE & POLING -----------------
app = Flask('')


@app.route('/')
def home():
  return 'Bot is alive!'


def run():
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = threading.Thread(target=run)
  t.start()


if __name__ == '__main__':
  keep_alive()
  try:
    bot.delete_webhook()
  except Exception as e:
    print(f'Webhook delete error: {e}')

  bot.infinity_polling()
