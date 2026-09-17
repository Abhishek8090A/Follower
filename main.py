import os
import random
import threading
import time
from flask import Flask
import telebot
from telebot import types

# ----------------- Configuration -----------------
TOKEN = '8818399396:AAGz1-xkSUprQUr8ST64AoC_ire81rObcEU'  # Your Bot Token
ADMIN_ID = 6262854630  # Your Telegram User ID
REQUIRED_CHANNEL = '@ksp008h'  # Your Telegram Channel Username
# ------------------------------------------------

bot = telebot.TeleBot(TOKEN)

# Database (Memory Storage)
users = {}
user_state = {}
temp_promotion_data = {}
pending_approvals = {}  # Pending screenshots for admin approval

# Dynamic Settings
bot_settings = {
    'reward_coins': 10,
    'cost_per_hour': 20,  # Cost per hour
    'daily_bonus': 50,  # Daily bonus coins
    'referral_bonus': 15,  # Referral bonus
    'support_contact': 'https://t.me/Helpbot655_bot',  # Default Support Link
    'coin_packages': [],  # VIP Packages list
}

# ----------------- Promotion Pools -----------------
ig_follow_pool = []
ig_like_pool = []
yt_sub_pool = []
tg_channel_pool = []   
fb_post_pool = []      
fb_reel_pool = []      
yt_video_pool = []     
snapchat_pool = []     # New Snapchat Pool


# ----------------- Auto-Cleanup Background Worker -----------------
def cleanup_expired_promotions():
  while True:
    current_time = time.time()
    global ig_follow_pool, ig_like_pool, yt_sub_pool
    global tg_channel_pool, fb_post_pool, fb_reel_pool, yt_video_pool, snapchat_pool
    
    ig_follow_pool = [item for item in ig_follow_pool if item['expires_at'] > current_time]
    ig_like_pool = [item for item in ig_like_pool if item['expires_at'] > current_time]
    yt_sub_pool = [item for item in yt_sub_pool if item['expires_at'] > current_time]
    tg_channel_pool = [item for item in tg_channel_pool if item['expires_at'] > current_time]
    fb_post_pool = [item for item in fb_post_pool if item['expires_at'] > current_time]
    fb_reel_pool = [item for item in fb_reel_pool if item['expires_at'] > current_time]
    yt_video_pool = [item for item in yt_video_pool if item['expires_at'] > current_time]
    snapchat_pool = [item for item in snapchat_pool if item['expires_at'] > current_time]
    
    time.sleep(60)


threading.Thread(target=cleanup_expired_promotions, daemon=True).start()


# ----------------- Channel Membership Check Function -----------------
def check_subscription(user_id):
  try:
    member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
    if member.status in ['member', 'administrator', 'creator']:
      return True
  except Exception as e:
    print(f'Error checking subscription: {e}')
  return False


# ----------------- Keyboard Generators -----------------
def get_main_menu(user_id):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      types.KeyboardButton('📸 IG Follow Tasks'),
      types.KeyboardButton('❤️ IG Like Tasks'),
  )
  markup.add(
      types.KeyboardButton('▶️ YT Sub Tasks'),
      types.KeyboardButton('🎥 YT Video Tasks'),
  )
  markup.add(
      types.KeyboardButton('📢 TG Channel Tasks'),
      types.KeyboardButton('👍 FB Post Tasks'),
  )
  markup.add(
      types.KeyboardButton('🎞 FB Reel Tasks'),
      types.KeyboardButton('👻 Snapchat Tasks'), # New Snapchat Button
  )
  markup.add(
      types.KeyboardButton('➕ Promote Link'),
      types.KeyboardButton('🎁 Daily Bonus'),
  )
  markup.add(
      types.KeyboardButton('👥 Invite & Earn (Referral)'),
      types.KeyboardButton('💰 My Profile'),
  )
  markup.add(
      types.KeyboardButton('💳 Buy Coins (Premium)'),
      types.KeyboardButton('🎧 Support / Help')
  )

  if user_id == ADMIN_ID:
    markup.add(types.KeyboardButton('👑 Admin Panel'))

  return markup


def get_admin_menu():
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      types.KeyboardButton('🔔 Pending Task Approvals'),
      types.KeyboardButton('📢 Broadcast Message')
  )
  markup.add(
      types.KeyboardButton('⚙️ Set Reward Coins'),
      types.KeyboardButton('⚙️ Set Cost Per Hour'),
  )
  markup.add(
      types.KeyboardButton('⚙️ Set Daily Bonus'),
      types.KeyboardButton('⚙️ Set Referral Bonus'),
  )
  markup.add(
      types.KeyboardButton('⚙️ Set Support Contact'),
      types.KeyboardButton('➕ Add Coins to User')
  )
  markup.add(
      types.KeyboardButton('💳 Add Coin Package'),
      types.KeyboardButton('🗑️ Clear Packages')
  )
  markup.add(types.KeyboardButton('🏠 Back to Main Menu'))
  return markup


# ----------------- Start Command -----------------
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
        '❌ **You must join our channel to use this bot!**\n\n'
        f'First, join our channel by clicking the button below: 👉'
        f' {REQUIRED_CHANNEL}\n\n'
        'After joining, click the **\'Check Membership\'** button.',
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
            '🎉 **New Referral!**\nA user joined the bot using your link. You received'
            f" **+{bot_settings['referral_bonus']} Coins**!",
            parse_mode='Markdown',
        )
      except:
        pass

  welcome_text = (
      '👋 **Welcome to the Multi-Promote Bot!**\n\n'
      'Here you can earn coins by completing tasks and promote your links on an hourly or daily basis.\n\n'
      '👇 Select an option from the menu below:'
  )
  bot.send_message(
      message.chat.id,
      welcome_text,
      parse_mode='Markdown',
      reply_markup=get_main_menu(user_id),
  )


# ----------------- Photo/Screenshot Handler -----------------
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
        '⏳ **Your screenshot has been sent to the admin for verification!**\n\n'
        'Please wait **10 to 15 minutes**. Coins will be added after the admin reviews it.',
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
            '🔔 **New Task Screenshot Received!**\n\n'
            f"👤 User: @{message.from_user.username or 'No Username'} (ID:"
            f' `{user_id}`)\n'
            f'🎯 Target: `{target_val}`\n'
            f"🎁 Reward: `{bot_settings['reward_coins']} Coins`"
        ),
        parse_mode='Markdown',
        reply_markup=admin_markup,
    )
  else:
    bot.send_message(
        message.chat.id,
        '❌ Please select a task first and proceed according to the rules.',
    )


# ----------------- Text and State Handler -----------------
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

  # --- Admin Cancel Action ---
  if text == '❌ Cancel' and user_id == ADMIN_ID:
    user_state[user_id] = None
    bot.send_message(message.chat.id, '❌ Action cancelled.', reply_markup=get_admin_menu())
    return

  # --- Custom Days Input Handler ---
  if current_state == 'WAITING_CUSTOM_DAYS_INPUT':
    try:
      days = int(text.strip())
      if days <= 0:
        bot.send_message(message.chat.id, "❌ Please enter 1 or more days.")
        return

      hours = days * 24
      total_cost = hours * bot_settings['cost_per_hour']

      if users[user_id]['balance'] < total_cost:
        bot.send_message(
            message.chat.id,
            f'❌ Insufficient balance! You need `{total_cost} Coins` for {days} days ({hours} hours).\n'
            f'💰 Your current balance: `{users[user_id]["balance"]} Coins`',
            parse_mode='Markdown'
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
      elif promo_info['type'] == 'WAITING_TG_CHANNEL':
        tg_channel_pool.append(pool_item)
      elif promo_info['type'] == 'WAITING_FB_POST':
        fb_post_pool.append(pool_item)
      elif promo_info['type'] == 'WAITING_FB_REEL':
        fb_reel_pool.append(pool_item)
      elif promo_info['type'] == 'WAITING_YT_VIDEO':
        yt_video_pool.append(pool_item)
      elif promo_info['type'] == 'WAITING_SNAPCHAT':
        snapchat_pool.append(pool_item)

      users[user_id]['promotions'].append(pool_item)
      user_state[user_id] = None
      temp_promotion_data.pop(user_id, None)

      bot.send_message(
          message.chat.id,
          f'✅ **Promoted Successfully!**\nYour link will be live for the next **{days} days**.\n'
          f'💸 `{total_cost} Coins` have been deducted from your account.',
          reply_markup=get_main_menu(user_id),
          parse_mode='Markdown',
      )
    except ValueError:
      bot.send_message(message.chat.id, '❌ Please send numbers only (e.g., 5, 10, 15).')
    return


  # 1. Promote Input States
  if current_state in [
      'WAITING_IG_FOLLOW', 'WAITING_IG_LIKE', 'WAITING_YT_SUB',
      'WAITING_TG_CHANNEL', 'WAITING_FB_POST', 'WAITING_FB_REEL', 
      'WAITING_YT_VIDEO', 'WAITING_SNAPCHAT'
  ]:
    entry = text.strip()

    # ----------------- VALIDATION -----------------
    if current_state == 'WAITING_IG_FOLLOW':
      if 'instagram.com' not in entry and not entry.startswith('@'):
        if len(entry) < 3 or ' ' in entry or entry.isnumeric():
          bot.send_message(message.chat.id, "❌ Invalid input! Please enter a valid Instagram Profile Link or Username.")
          return
      entry = entry.lstrip('@')
      if 'instagram.com' in entry:
        try:
          entry = entry.split('instagram.com/')[-1].split('/')[0].split('?')[0].replace('@', '')
        except:
          pass
      if len(entry) == 0:
        bot.send_message(message.chat.id, "❌ Invalid input. Please try again.")
        return

    elif current_state == 'WAITING_IG_LIKE':
      if not (entry.startswith('http') and 'instagram.com' in entry):
        bot.send_message(message.chat.id, "❌ Invalid link! Please enter a valid Instagram Post or Reel Link.")
        return

    elif current_state == 'WAITING_YT_SUB':
      if not (entry.startswith('http') and ('youtube.com' in entry or 'youtu.be' in entry)):
        bot.send_message(message.chat.id, "❌ Invalid link! Please enter a valid YouTube Channel Link.")
        return

    elif current_state == 'WAITING_TG_CHANNEL':
      if not ('t.me/' in entry or entry.startswith('@')):
        bot.send_message(message.chat.id, "❌ Invalid input! Please enter a valid Telegram Channel Link or Username (e.g. @channel or https://t.me/channel).")
        return

    elif current_state == 'WAITING_FB_POST':
      if not (entry.startswith('http') and 'facebook.com' in entry):
        bot.send_message(message.chat.id, "❌ Invalid link! Please enter a valid Facebook Post Link.")
        return

    elif current_state == 'WAITING_FB_REEL':
      if not (entry.startswith('http') and 'facebook.com' in entry):
        bot.send_message(message.chat.id, "❌ Invalid link! Please enter a valid Facebook Reel Link.")
        return

    elif current_state == 'WAITING_YT_VIDEO':
      if not (entry.startswith('http') and ('youtube.com' in entry or 'youtu.be' in entry)):
        bot.send_message(message.chat.id, "❌ Invalid link! Please enter a valid YouTube Video Link.")
        return

    elif current_state == 'WAITING_SNAPCHAT':
      if 'snapchat.com' not in entry and not entry.startswith('@') and len(entry) < 3:
        bot.send_message(message.chat.id, "❌ Invalid input! Please enter a valid Snapchat Profile Link or Username.")
        return
      entry = entry.lstrip('@')
    # ----------------------------------------------------------------------

    temp_promotion_data[user_id] = {'type': current_state, 'target': entry}
    user_state[user_id] = 'WAITING_HOURS'

    cost_1h = bot_settings['cost_per_hour']
    cost_1d = cost_1h * 24
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton('1 Hour', callback_data='hrs_1'),
        types.InlineKeyboardButton('6 Hours', callback_data='hrs_6'),
        types.InlineKeyboardButton('12 Hours', callback_data='hrs_12'),
    )
    markup.add(
        types.InlineKeyboardButton('1 Day', callback_data='hrs_24'),
        types.InlineKeyboardButton('2 Days', callback_data='hrs_48'),
        types.InlineKeyboardButton('3 Days', callback_data='hrs_72'),
    )
    markup.add(
        types.InlineKeyboardButton('7 Days (1 Week)', callback_data='hrs_168')
    )
    markup.add(
        types.InlineKeyboardButton('✏️ Enter Custom Days', callback_data='custom_days')
    )
    
    bot.send_message(
        message.chat.id,
        f'⏳ **Username/Link saved:** `{entry}`\n\n'
        f'How long do you want to keep it live?\n'
        f'Rate: `{cost_1h} Coins` per hour | `{cost_1d} Coins` per day',
        parse_mode='Markdown',
        reply_markup=markup,
    )
    return

  # 2. Admin Panel States
  if user_id == ADMIN_ID and current_state in [
      'SET_REWARD', 'SET_COST', 'SET_BONUS', 'SET_REFERRAL',
      'ADD_COINS_INPUT', 'SET_SUPPORT_CONTACT', 'ADD_COIN_PACKAGE', 'WAITING_BROADCAST_MESSAGE'
  ]:
    if current_state == 'WAITING_BROADCAST_MESSAGE':
      bot.send_message(message.chat.id, "⏳ Broadcasting message to all users... Please wait.")
      success = 0
      failed = 0
      for uid in users.keys():
        try:
          bot.send_message(uid, f"📢 **Broadcast Message:**\n\n{text}", parse_mode='Markdown')
          success += 1
        except Exception as e:
          failed += 1
      
      bot.send_message(
          message.chat.id,
          f"✅ **Broadcast Complete!**\n\n🟢 Successfully Sent: `{success}`\n🔴 Failed: `{failed}`",
          parse_mode='Markdown',
          reply_markup=get_admin_menu()
      )
      user_state[user_id] = None
      return

    elif current_state == 'SET_REWARD':
      try:
        bot_settings['reward_coins'] = int(text.strip())
        bot.send_message(
            message.chat.id,
            f"✅ Updated! New Reward: {bot_settings['reward_coins']} Coins",
            reply_markup=get_admin_menu(),
        )
      except ValueError:
        bot.send_message(message.chat.id, '❌ Please send numbers only.')
      user_state[user_id] = None
      return

    elif current_state == 'SET_COST':
      try:
        bot_settings['cost_per_hour'] = int(text.strip())
        bot.send_message(
            message.chat.id,
            f"✅ Updated! New Cost: {bot_settings['cost_per_hour']} Coins",
            reply_markup=get_admin_menu(),
        )
      except ValueError:
        bot.send_message(message.chat.id, '❌ Please send numbers only.')
      user_state[user_id] = None
      return

    elif current_state == 'SET_BONUS':
      try:
        bot_settings['daily_bonus'] = int(text.strip())
        bot.send_message(
            message.chat.id,
            f"✅ Updated! New Daily Bonus: {bot_settings['daily_bonus']} Coins",
            reply_markup=get_admin_menu(),
        )
      except ValueError:
        bot.send_message(message.chat.id, '❌ Please send numbers only.')
      user_state[user_id] = None
      return

    elif current_state == 'SET_REFERRAL':
      try:
        bot_settings['referral_bonus'] = int(text.strip())
        bot.send_message(
            message.chat.id,
            f"✅ Updated! New Referral Bonus: {bot_settings['referral_bonus']} Coins",
            reply_markup=get_admin_menu(),
        )
      except ValueError:
        bot.send_message(message.chat.id, '❌ Please send numbers only.')
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
                'balance': 0, 'promotions': [], 'last_bonus_time': 0,
                'completed_tasks': [], 'referred_by': None, 'referral_count': 0,
            }
          users[target_user_id]['balance'] += coins_to_add
          bot.send_message(
              message.chat.id,
              '✅ Coins added successfully!',
              reply_markup=get_admin_menu(),
          )
        else:
          bot.send_message(
              message.chat.id,
              '❌ Invalid format! Example: `123456 500`',
              parse_mode='Markdown',
          )
      except Exception as e:
        bot.send_message(message.chat.id, f'❌ Error: {e}')
      user_state[user_id] = None
      return

    elif current_state == 'SET_SUPPORT_CONTACT':
      bot_settings['support_contact'] = text.strip()
      bot.send_message(
          message.chat.id, 
          f"✅ Support link updated!\nNew Support: `{bot_settings['support_contact']}`", 
          parse_mode='Markdown',
          reply_markup=get_admin_menu()
      )
      user_state[user_id] = None
      return

    elif current_state == 'ADD_COIN_PACKAGE':
      bot_settings['coin_packages'].append(text.strip())
      bot.send_message(
          message.chat.id, 
          f"✅ New VIP package added!\nPackage: `{text.strip()}`", 
          parse_mode='Markdown',
          reply_markup=get_admin_menu()
      )
      user_state[user_id] = None
      return

  # 3. Admin Panel Button Clicks
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

  elif text == '📢 Broadcast Message' and user_id == ADMIN_ID:
    user_state[user_id] = 'WAITING_BROADCAST_MESSAGE'
    cancel_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_markup.add(types.KeyboardButton('❌ Cancel'))
    bot.send_message(
        message.chat.id,
        "📝 **Send the message you want to broadcast to all users.**\n\n(Type your message and send it here)",
        parse_mode='Markdown',
        reply_markup=cancel_markup
    )
    return

  elif text == '🔔 Pending Task Approvals' and user_id == ADMIN_ID:
    if not pending_approvals:
      bot.send_message(
          message.chat.id, '📭 There are no pending screenshots for approval at the moment.'
      )
    else:
      bot.send_message(
          message.chat.id,
          f'📋 **Total pending requests:** `{len(pending_approvals)}`',
          parse_mode='Markdown',
      )
      count = 1
      for req_id, data in pending_approvals.items():
        username = data.get('username', 'No Username')
        u_id = data.get('user_id', 'Unknown')
        target = data.get('target', 'None')
        reward = data.get('reward', 0)

        msg = f"**{count}.** 👤 **User:** @{username} (ID: `{u_id}`)\n"
        msg += f"🎯 **Target:** `{target}`\n"
        msg += f"💰 **Reward:** `{reward} Coins`"

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton('✅ Approve', callback_data=f'app_{req_id}'),
            types.InlineKeyboardButton('❌ Reject', callback_data=f'rej_{req_id}')
        )

        bot.send_message(
            message.chat.id,
            msg,
            parse_mode='Markdown',
            reply_markup=markup
        )
        count += 1
    return

  elif text == '🏠 Back to Main Menu' and user_id == ADMIN_ID:
    user_state[user_id] = None
    bot.send_message(
        message.chat.id,
        '🏠 Back to Main Menu:',
        reply_markup=get_main_menu(user_id),
    )
    return

  elif text == '⚙️ Set Reward Coins' and user_id == ADMIN_ID:
    user_state[user_id] = 'SET_REWARD'
    bot.send_message(
        message.chat.id, 'Enter the new task reward amount (numbers only):'
    )
    return

  elif text == '⚙️ Set Cost Per Hour' and user_id == ADMIN_ID:
    user_state[user_id] = 'SET_COST'
    bot.send_message(
        message.chat.id,
        'Enter the hourly promotion cost (numbers only):',
    )
    return

  elif text == '⚙️ Set Daily Bonus' and user_id == ADMIN_ID:
    user_state[user_id] = 'SET_BONUS'
    bot.send_message(
        message.chat.id,
        'Enter the new daily bonus amount (numbers only):',
    )
    return

  elif text == '⚙️ Set Referral Bonus' and user_id == ADMIN_ID:
    user_state[user_id] = 'SET_REFERRAL'
    bot.send_message(
        message.chat.id,
        'Enter the new referral bonus amount (numbers only):',
    )
    return

  elif text == '➕ Add Coins to User' and user_id == ADMIN_ID:
    user_state[user_id] = 'ADD_COINS_INPUT'
    bot.send_message(
        message.chat.id,
        '➕ Send in the correct format:\n`User_ID Space Coins`\nExample: `123456 500`',
        parse_mode='Markdown',
    )
    return

  elif text == '⚙️ Set Support Contact' and user_id == ADMIN_ID:
    user_state[user_id] = 'SET_SUPPORT_CONTACT'
    bot.send_message(message.chat.id, 'Send the new support username or link\n(Example: `@YourNewBot` or `https://t.me/yourusername`):', parse_mode='Markdown')
    return

  elif text == '💳 Add Coin Package' and user_id == ADMIN_ID:
    user_state[user_id] = 'ADD_COIN_PACKAGE'
    bot.send_message(message.chat.id, 'Send the details of the new premium package.\nExample: `$10 = 1000 Coins` or `₹50 - 50,000 Coins`', parse_mode='Markdown')
    return

  elif text == '🗑️ Clear Packages' and user_id == ADMIN_ID:
    bot_settings['coin_packages'] = []
    bot.send_message(message.chat.id, '✅ All coin packages deleted successfully!', reply_markup=get_admin_menu())
    return

  # 4. Main Menu Buttons
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
          '⏳ You have already claimed today\'s bonus!\n'
          f'You will get the next bonus after **{hours} hours {minutes} minutes**.',
          parse_mode='Markdown',
      )
    else:
      bonus_amt = bot_settings['daily_bonus']
      users[user_id]['balance'] += bonus_amt
      users[user_id]['last_bonus_time'] = current_time
      bot.send_message(
          message.chat.id,
          '🎉 Congratulations! You have successfully received a daily bonus of'
          f' **+{bonus_amt} Coins**!',
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
        f'Invite your friends and earn **{bonus} Coins** for each successful referral!\n\n'
        f'🔗 **Your Referral Link:**\n`{referral_link}`\n\n'
        f'📊 **Total Invites:** `{ref_count}`\n\n'
        '⚠️ *Note: You will only receive points if your friend starts the bot and joins our channel.*'
    )
    markup = types.InlineKeyboardMarkup()
    share_url = (
        'https://t.me/share/url?url='
        + referral_link
        + '&text=🌟%20Earn%20points%20and%20promote%20using%20this%20bot!'
    )
    markup.add(
        types.InlineKeyboardButton('📤 Share with friends', url=share_url)
    )

    bot.send_message(
        message.chat.id, msg, parse_mode='Markdown', reply_markup=markup
    )

  elif text == '💳 Buy Coins (Premium)':
    packages = bot_settings.get('coin_packages', [])
    support = bot_settings.get('support_contact', 'https://t.me/Helpbot655_bot')
    
    if support.startswith('@'):
        support_url = f"https://t.me/{support.replace('@', '')}"
    elif not support.startswith('http'):
        support_url = f"https://t.me/{support}"
    else:
        support_url = support

    if not packages:
      msg = "😔 No premium coin packages are currently available. Please check back later or contact support."
    else:
      msg = "💎 **Premium Coin Packages** 💎\n\nHere is the list of our available packages:\n\n"
      for i, pkg in enumerate(packages, 1):
        msg += f"📦 **{i}.** `{pkg}`\n"
      msg += "\n🛒 **To Buy:** Click the button below to contact the admin and state your desired package."

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Buy Now (Contact Admin)", url=support_url))
    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

  elif text == '🎧 Support / Help':
    support = bot_settings.get('support_contact', 'https://t.me/Helpbot655_bot')
    
    if support.startswith('@'):
        support_url = f"https://t.me/{support.replace('@', '')}"
    elif not support.startswith('http'):
        support_url = f"https://t.me/{support}"
    else:
        support_url = support

    support_markup = types.InlineKeyboardMarkup()
    support_markup.add(types.InlineKeyboardButton('💬 Contact Support', url=support_url))
    
    bot.send_message(
        message.chat.id,
        f'📞 **Customer Support**\n\nIf you have any issues or want to buy coins, you can directly chat with us by clicking the button below.\n\n👤 Support: `{support}`',
        parse_mode='Markdown',
        reply_markup=support_markup
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

  # ====================== TASKS HANDLING ======================

  elif text == '📸 IG Follow Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [item for item in ig_follow_pool if item['target'] not in completed]

    if len(available_pool) == 0:
      bot.send_message(message.chat.id, '❌ There are no new IG follow tasks available for you right now.')
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
    markup.add(types.InlineKeyboardButton('✅ Task Completed (Send Screenshot)', callback_data='ask_screenshot'))
    
    bot.send_message(
        message.chat.id,
        f'📌 **Follow this new account:**\n👉 `{target_val}`\n\nAfter following, click the button below to send a **Screenshot**.',
        reply_markup=markup,
        parse_mode='Markdown',
    )

  elif text == '❤️ IG Like Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [item for item in ig_like_pool if item['target'] not in completed]

    if len(available_pool) == 0:
      bot.send_message(message.chat.id, '❌ No new IG like tasks available right now.')
      return

    item = random.choice(available_pool)
    user_state[f'temp_target_{user_id}'] = item['target']

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('❤️ Like Post', url=item['target']))
    markup.add(types.InlineKeyboardButton('✅ Task Completed (Send Screenshot)', callback_data='ask_screenshot'))
    
    bot.send_message(
        message.chat.id, '📌 **Like this new post and send a screenshot:**',
        reply_markup=markup, parse_mode='Markdown'
    )

  elif text == '▶️ YT Sub Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [item for item in yt_sub_pool if item['target'] not in completed]

    if len(available_pool) == 0:
      bot.send_message(message.chat.id, '❌ No new YouTube tasks available right now.')
      return

    item = random.choice(available_pool)
    user_state[f'temp_target_{user_id}'] = item['target']

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('▶️ Subscribe Channel', url=item['target']))
    markup.add(types.InlineKeyboardButton('✅ Task Completed (Send Screenshot)', callback_data='ask_screenshot'))
    
    bot.send_message(
        message.chat.id, '📌 **Subscribe to this new channel and send a screenshot:**',
        reply_markup=markup, parse_mode='Markdown'
    )

  elif text == '📢 TG Channel Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [item for item in tg_channel_pool if item['target'] not in completed]

    if len(available_pool) == 0:
      bot.send_message(message.chat.id, '❌ No new Telegram channel tasks available right now.')
      return

    item = random.choice(available_pool)
    user_state[f'temp_target_{user_id}'] = item['target']
    
    target_val = item['target']
    if target_val.startswith('@'):
      channel_url = f"https://t.me/{target_val.replace('@', '')}"
    else:
      channel_url = target_val

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('📢 Join Channel', url=channel_url))
    markup.add(types.InlineKeyboardButton('✅ Task Completed (Send Screenshot)', callback_data='ask_screenshot'))
    
    bot.send_message(
        message.chat.id, '📌 **Join this Telegram channel and send a screenshot:**',
        reply_markup=markup, parse_mode='Markdown'
    )

  elif text == '👍 FB Post Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [item for item in fb_post_pool if item['target'] not in completed]

    if len(available_pool) == 0:
      bot.send_message(message.chat.id, '❌ No new Facebook Post tasks available right now.')
      return

    item = random.choice(available_pool)
    user_state[f'temp_target_{user_id}'] = item['target']

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('👍 Like FB Post', url=item['target']))
    markup.add(types.InlineKeyboardButton('✅ Task Completed (Send Screenshot)', callback_data='ask_screenshot'))
    
    bot.send_message(
        message.chat.id, '📌 **Like this Facebook post and send a screenshot:**',
        reply_markup=markup, parse_mode='Markdown'
    )

  elif text == '🎞 FB Reel Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [item for item in fb_reel_pool if item['target'] not in completed]

    if len(available_pool) == 0:
      bot.send_message(message.chat.id, '❌ No new Facebook Reel tasks available right now.')
      return

    item = random.choice(available_pool)
    user_state[f'temp_target_{user_id}'] = item['target']

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🎞 Watch/Like Reel', url=item['target']))
    markup.add(types.InlineKeyboardButton('✅ Task Completed (Send Screenshot)', callback_data='ask_screenshot'))
    
    bot.send_message(
        message.chat.id, '📌 **Watch/Like this Facebook Reel and send a screenshot:**',
        reply_markup=markup, parse_mode='Markdown'
    )

  elif text == '🎥 YT Video Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [item for item in yt_video_pool if item['target'] not in completed]

    if len(available_pool) == 0:
      bot.send_message(message.chat.id, '❌ No new YouTube Video tasks available right now.')
      return

    item = random.choice(available_pool)
    user_state[f'temp_target_{user_id}'] = item['target']

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🎥 Watch Video', url=item['target']))
    markup.add(types.InlineKeyboardButton('✅ Task Completed (Send Screenshot)', callback_data='ask_screenshot'))
    
    bot.send_message(
        message.chat.id, '📌 **Watch/Like this YouTube Video and send a screenshot:**',
        reply_markup=markup, parse_mode='Markdown'
    )

  # ---------- NEW SNAPCHAT TASK HANDLER ----------
  elif text == '👻 Snapchat Tasks':
    completed = users[user_id].get('completed_tasks', [])
    available_pool = [item for item in snapchat_pool if item['target'] not in completed]

    if len(available_pool) == 0:
      bot.send_message(message.chat.id, '❌ No new Snapchat tasks available right now.')
      return

    item = random.choice(available_pool)
    user_state[f'temp_target_{user_id}'] = item['target']
    
    target_val = item['target']
    if target_val.startswith('http'):
      snap_url = target_val
    else:
      snap_url = f'https://www.snapchat.com/add/{target_val}'

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('👻 Add / View Snapchat', url=snap_url))
    markup.add(types.InlineKeyboardButton('✅ Task Completed (Send Screenshot)', callback_data='ask_screenshot'))
    
    bot.send_message(
        message.chat.id, '📌 **Add this user or view their Snapchat and send a screenshot:**',
        reply_markup=markup, parse_mode='Markdown'
    )
  # -----------------------------------------------

  elif text == '➕ Promote Link':
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('📸 IG Follow', callback_data='add_ig_follow'),
        types.InlineKeyboardButton('❤️ IG Like/Reel', callback_data='add_ig_like')
    )
    markup.add(
        types.InlineKeyboardButton('▶️ YT Sub', callback_data='add_yt_sub'),
        types.InlineKeyboardButton('🎥 YT Video', callback_data='add_yt_video')
    )
    markup.add(
        types.InlineKeyboardButton('📢 TG Channel', callback_data='add_tg_channel'),
        types.InlineKeyboardButton('👍 FB Post', callback_data='add_fb_post')
    )
    markup.add(
        types.InlineKeyboardButton('🎞 FB Reel', callback_data='add_fb_reel'),
        types.InlineKeyboardButton('👻 Snapchat', callback_data='add_snapchat') # New Snapchat Button
    )

    bot.send_message(
        message.chat.id,
        '🚀 What do you want to promote?',
        reply_markup=markup,
        parse_mode='Markdown',
    )

  else:
    bot.send_message(
        message.chat.id, '❌ Please use the menu options provided below.'
    )


# ----------------- Callback Handlers -----------------
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
  user_id = call.from_user.id

  if call.data.startswith('check_sub'):
    parts = call.data.split('_')
    referrer_id = int(parts[2]) if len(parts) > 2 else 0

    if check_subscription(user_id):
      bot.answer_callback_query(call.id, '✅ Channel joined successfully!')
      try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
      except:
        pass

      if user_id not in users:
        users[user_id] = {
            'balance': 0, 'promotions': [], 'last_bonus_time': 0,
            'completed_tasks': [], 'referred_by': None, 'referral_count': 0,
        }

        if referrer_id and referrer_id in users and referrer_id != user_id:
          users[user_id]['referred_by'] = referrer_id
          users[referrer_id]['referral_count'] = users[referrer_id].get('referral_count', 0) + 1
          users[referrer_id]['balance'] += bot_settings['referral_bonus']
          try:
            bot.send_message(
                referrer_id,
                '🎉 **New Referral!**\nA user joined the bot and channel using your link. You received'
                f" **+{bot_settings['referral_bonus']} Coins**!",
                parse_mode='Markdown',
            )
          except:
            pass

      bot.send_message(
          call.message.chat.id,
          '👋 Welcome!',
          reply_markup=get_main_menu(user_id),
      )
    else:
      bot.answer_callback_query(call.id, '❌ You have not joined the channel yet!', show_alert=True)

  elif call.data == 'ask_screenshot':
    user_state[user_id] = 'WAITING_SCREENSHOT'
    current_target = user_state.get(f'temp_target_{user_id}')
    user_state[f'target_{user_id}'] = current_target

    bot.answer_callback_query(call.id, 'Please upload the screenshot!')
    bot.send_message(
        call.message.chat.id,
        '📸 Please send the **Screenshot** of the completed task here in the chat as a photo.',
    )

  elif call.data.startswith('app_') or call.data.startswith('rej_'):
    if user_id != ADMIN_ID:
      bot.answer_callback_query(
          call.id, '❌ You are not an admin!', show_alert=True
      )
      return

    action, req_id = call.data.split('_', 1)

    if req_id not in pending_approvals:
      bot.answer_callback_query(
          call.id,
          '❌ This request has already been processed!',
          show_alert=True,
      )
      return

    data = pending_approvals.pop(req_id)
    target_user_id = data['user_id']
    reward = data['reward']
    task_target = data['target']

    if target_user_id not in users:
      users[target_user_id] = {
          'balance': 0, 'promotions': [], 'last_bonus_time': 0,
          'completed_tasks': [], 'referred_by': None, 'referral_count': 0,
      }

    if action == 'app':
      users[target_user_id]['balance'] += reward

      if (task_target and task_target not in users[target_user_id]['completed_tasks']):
        users[target_user_id]['completed_tasks'].append(task_target)

      bot.answer_callback_query(call.id, '✅ Approved and coins added!')
      try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f'{call.message.caption}\n\n🟢 **Status: APPROVED (+{reward} Coins added)**',
                parse_mode='Markdown',
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f'{call.message.text}\n\n🟢 **Status: APPROVED (+{reward} Coins added)**',
                parse_mode='Markdown',
            )
      except:
        pass

      try:
        bot.send_message(
            target_user_id,
            '🎉 **Congratulations! Your task has been approved.**\n'
            f'**+{reward} Coins** have been added to your account!',
            parse_mode='Markdown',
        )
      except:
        pass

    elif action == 'rej':
      bot.answer_callback_query(call.id, '❌ Task Rejected!')
      try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f'{call.message.caption}\n\n🔴 **Status: REJECTED**',
                parse_mode='Markdown',
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f'{call.message.text}\n\n🔴 **Status: REJECTED**',
                parse_mode='Markdown',
            )
      except:
        pass

      try:
        bot.send_message(
            target_user_id,
            '❌ **Your task screenshot was rejected by the admin.** Please send a correct screenshot again.',
            parse_mode='Markdown',
        )
      except:
        pass

  # ====================== PROMOTE SELECTIONS ======================

  elif call.data == 'add_ig_follow':
    user_state[user_id] = 'WAITING_IG_FOLLOW'
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, '📸 **Send your Instagram Username or Profile Link:**', parse_mode='Markdown')

  elif call.data == 'add_ig_like':
    user_state[user_id] = 'WAITING_IG_LIKE'
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, '❤️ **Send the full link to your Instagram Post or Reel:**', parse_mode='Markdown')

  elif call.data == 'add_yt_sub':
    user_state[user_id] = 'WAITING_YT_SUB'
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, '▶️ **Send the full link to your YouTube Channel:**', parse_mode='Markdown')

  elif call.data == 'add_yt_video':
    user_state[user_id] = 'WAITING_YT_VIDEO'
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, '🎥 **Send the full link to your YouTube Video:**', parse_mode='Markdown')

  elif call.data == 'add_tg_channel':
    user_state[user_id] = 'WAITING_TG_CHANNEL'
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, '📢 **Send your Telegram Channel Link or @username:**', parse_mode='Markdown')

  elif call.data == 'add_fb_post':
    user_state[user_id] = 'WAITING_FB_POST'
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, '👍 **Send the full link to your Facebook Post:**', parse_mode='Markdown')

  elif call.data == 'add_fb_reel':
    user_state[user_id] = 'WAITING_FB_REEL'
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, '🎞 **Send the full link to your Facebook Reel:**', parse_mode='Markdown')
    
  elif call.data == 'add_snapchat':
    user_state[user_id] = 'WAITING_SNAPCHAT'
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, '👻 **Send your Snapchat Username or Profile Link:**', parse_mode='Markdown')


  elif call.data == 'custom_days':
    if user_id not in temp_promotion_data:
      bot.answer_callback_query(call.id, '❌ Something went wrong! Please enter the link again.', show_alert=True)
      return

    user_state[user_id] = 'WAITING_CUSTOM_DAYS_INPUT'
    bot.answer_callback_query(call.id)
    
    cost_per_day = bot_settings['cost_per_hour'] * 24
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f'📅 **Custom Days**\n\n'
             f'Please type in the chat how many **days** you want to promote for (Example: 5, 10, 30).\n\n'
             f'💡 1 Day charge: `{cost_per_day} Coins`',
        parse_mode='Markdown'
    )
    return

  elif call.data.startswith('hrs_'):
    if user_id not in temp_promotion_data:
      bot.answer_callback_query(call.id, '❌ Something went wrong!', show_alert=True)
      return

    hours = int(call.data.split('_')[1])
    total_cost = hours * bot_settings['cost_per_hour']

    if users[user_id]['balance'] < total_cost:
      bot.answer_callback_query(
          call.id, f'❌ Insufficient balance! {total_cost} Coins required.', show_alert=True,
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
    elif promo_info['type'] == 'WAITING_TG_CHANNEL':
      tg_channel_pool.append(pool_item)
    elif promo_info['type'] == 'WAITING_FB_POST':
      fb_post_pool.append(pool_item)
    elif promo_info['type'] == 'WAITING_FB_REEL':
      fb_reel_pool.append(pool_item)
    elif promo_info['type'] == 'WAITING_YT_VIDEO':
      yt_video_pool.append(pool_item)
    elif promo_info['type'] == 'WAITING_SNAPCHAT':
      snapchat_pool.append(pool_item)

    users[user_id]['promotions'].append(pool_item)
    user_state[user_id] = None
    temp_promotion_data.pop(user_id, None)

    try:
      bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
      pass

    bot.send_message(
        call.message.chat.id,
        '✅ **Successfully Promoted!**\n'
        f'`{total_cost} Coins` have been deducted.',
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
