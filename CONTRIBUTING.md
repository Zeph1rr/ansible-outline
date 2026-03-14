# Contributing to ansible-outline-deploy

Спасибо за интерес к проекту! Любые улучшения приветствуются.

## Как внести изменения

1. Форкни репозиторий
2. Создай ветку: `git checkout -b feature/my-improvement`
3. Внеси изменения и проверь их локально (см. ниже)
4. Сделай commit: `git commit -m "feat: описание изменения"`
5. Открой Pull Request в ветку `main`

## Проверка перед PR

```bash
pip install ansible ansible-lint
ansible-lint playbook.yml
ansible-lint uninstall.yml
```

## Что можно улучшить

- Поддержка новых параметров Outline API
- Тесты с Molecule
- Поддержка других дистрибутивов (Debian, CentOS)
- Документация на английском языке

## Стиль кода

- Задачи в YAML именуются в формате `Verb + object`: `Install Docker`, `Copy script to server`
- Все задачи имеют осмысленное поле `name`
- Идемпотентность обязательна — повторный запуск не должен давать `changed`
