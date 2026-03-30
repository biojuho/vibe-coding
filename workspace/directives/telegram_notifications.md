# Telegram Notifications Directive

> Joolife Hub execution scripts send operational alerts and daily summaries to Telegram Bot chats.

## 1. Goal
- Deliver scheduler failures and daily summaries outside the Streamlit UI.
- Keep Telegram integration in deterministic `execution/` scripts.
- Avoid coupling business logic directly to Telegram API calls inside pages.

## 2. Tools
- `execution/telegram_notifier.py`: Telegram Bot API helper and CLI.
- `execution/scheduler_engine.py`: emits scheduler event notifications.
- `execution/daily_report.py`: can send the generated report to Telegram.

## 3. Required Environment Variables
- `TELEGRAM_BOT_TOKEN`: Bot token from BotFather.
- `TELEGRAM_CHAT_ID`: target chat or group id.
- `TELEGRAM_ENABLED`: optional, defaults to enabled.
- `TELEGRAM_NOTIFY_SCHEDULER`: `none`, `failures`, or `all` (default: `failures`).

## 4. Setup Flow
1. Create a bot with BotFather and store the token in `.env`.
2. Send a message to the bot from the target chat.
3. Run `python workspace/execution/telegram_notifier.py updates --limit 10` to inspect recent updates and discover the chat id.
4. Save the chat id in `.env` as `TELEGRAM_CHAT_ID`.
5. Run `python workspace/execution/telegram_notifier.py check` and `python workspace/execution/telegram_notifier.py send --message "test"` to validate the connection.

## 5. Runtime Behavior
- Scheduler notifications are best-effort and must never break task persistence.
- Daily reports only send to Telegram when `--telegram` is requested.
- Keep messages short and operationally useful.

## 6. CLI Examples
```bash
python workspace/execution/telegram_notifier.py check
python workspace/execution/telegram_notifier.py updates --limit 10
python workspace/execution/telegram_notifier.py send --message "hello from Joolife"
python workspace/execution/daily_report.py --format markdown --telegram
```
