# VPN Billing Microservice API

REST API микросервис для управления пользователями и VPN-конфигурациями. 
Этот проект — бэкенд-часть сервиса для генерации ключей (Xray) и управления подписками.

## Технологический стек
* **Framework:** FastAPI
* **Database:** SQLite (aiosqlite)
* **ORM:** SQLAlchemy 2.0 (Асинхронная работа, Declarative Mapping)
* **Validation:** Pydantic V2
* **Architecture:** Clean Architecture (разделение на API, схемы и модели)

## Функционал
* Регистрация и управление профилями пользователей (Telegram ID интеграция).
* Генерация и привязка уникальных VPN конфигураций (UUID4) к пользователям.
* Изоляция базы данных от внешних интерфейсов через Pydantic-схемы.
