"""
Скрипт для тестирования подключения к Google Sheets API
Запусти: python test_connection.py
"""
import sys
import os

def test_imports():
    """Проверка установленных библиотек"""
    print("📦 Проверка зависимостей...")
    try:
        import gspread
        import fastapi
        import jose
        print("✅ Все библиотеки установлены")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("   Выполни: pip install -r requirements.txt")
        return False

def test_service_account():
    """Проверка наличия service account файла"""
    print("\n🔑 Проверка service_account.json...")
    if os.path.exists("service_account.json"):
        print("✅ Файл найден")
        return True
    else:
        print("❌ Файл service_account.json не найден!")
        print("   Скачай его из Google Cloud Console:")
        print("   https://console.cloud.google.com/")
        return False

def test_google_connection():
    """Тест подключения к Google API"""
    print("\n🌐 Тест подключения к Google Sheets API...")
    try:
        import gspread
        gc = gspread.service_account(filename="service_account.json")
        print("✅ Успешное подключение к Google API")
        print(f"   Service Account: {gc.auth.service_account_email}")
        return True
    except FileNotFoundError:
        print("❌ Файл service_account.json не найден")
        return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def test_spreadsheet_access(spreadsheet_id=None):
    """Тест доступа к конкретной таблице"""
    if not spreadsheet_id:
        print("\n⏭️  Пропуск теста доступа к таблице (ID не указан)")
        return True
    
    print(f"\n📊 Тест доступа к таблице {spreadsheet_id}...")
    try:
        import gspread
        gc = gspread.service_account(filename="service_account.json")
        sh = gc.open_by_key(spreadsheet_id)
        print(f"✅ Доступ получен: {sh.title}")
        print(f"   Листов: {len(sh.worksheets())}")
        for ws in sh.worksheets():
            print(f"   - {ws.title}")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        print("❌ Таблица не найдена или нет доступа!")
        print("   Убедись что Service Account добавлен в права доступа")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("=" * 60)
    print("🧪 SheetPro - Проверка подключения")
    print("=" * 60)
    
    # Запускаем все тесты
    results = []
    results.append(("Зависимости", test_imports()))
    results.append(("Service Account", test_service_account()))
    
    if results[-1][1]:  # Если service account есть
        results.append(("Google API", test_google_connection()))
    
    # Опционально: тест конкретной таблицы
    print("\n" + "=" * 60)
    sheet_id = input("📋 Введи ID таблицы для теста (Enter для пропуска): ").strip()
    if sheet_id:
        results.append(("Доступ к таблице", test_spreadsheet_access(sheet_id)))
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ:")
    print("=" * 60)
    for name, status in results:
        icon = "✅" if status else "❌"
        print(f"{icon} {name}")
    
    # Финальный статус
    all_passed = all(status for _, status in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("   Можно запускать сервер: python main.py")
    else:
        print("⚠️  ЕСТЬ ПРОБЛЕМЫ - исправь их перед запуском")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())