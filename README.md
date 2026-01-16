source venv/bin/activate
systemctl restart zabota_tables
systemctl status zabota_tables
journalctl -u zabota_tables -f

alembic revision --autogenerate -m "add_names_to_user"
alembic upgrade head

acc-zabota2@zabotawebservice.iam.gserviceaccount.com
acc-zabota@zabotawebservice.iam.gserviceaccount.com
acc-zabota3@zabotawebservice.iam.gserviceaccount.com
tftdy-77@veiwgsheets.iam.gserviceaccount.com





# 🚀 SheetPro - Прокси для Google Таблиц
Безопасный веб-сервис для работы с Google Sheets через собственный интерфейс.
