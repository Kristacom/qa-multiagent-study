@REQ-REG-002 @KAN-26 @registration @email @S6afbc1f1
Feature: Регистрация — валидация поля Email
  Как новый пользователь интернет-магазина
    Я хочу зарегистрироваться в системе с корректным email
    Чтобы получить доступ к личному кабинету

  @TC-SHOP-003 @ui @registration @email @validation @positive @smoke @p1
  Scenario: Корректный email (user@example.com) → ошибки нет, кнопка «Зарегистрироваться» активна (Positive)
    # AC3 REQ-REG-002: позитивная проверка валидации email.
    Given Открыта форма регистрации
    When Пользователь вводит в поле email значение 'user@example.com'
    Then Сообщение об ошибке не отображается
    And Кнопка «Зарегистрироваться» активна

  @TC-SHOP-004 @ui @registration @email @validation @negative @p1 @T8080b81b
  Scenario: Email без символа @ → ошибка «Некорректный email» (Negative)
    # AC1 REQ-REG-002. Ambiguity: поведение кнопки при невалидном email не описано — ожидается disabled.
    Given Открыта форма регистрации
    When Пользователь вводит email 'userexample.com' (символ @ отсутствует)
    And Пользователь уводит фокус с поля email или пытается отправить форму
    Then Отображается сообщение об ошибке «Некорректный email»
    And Кнопка «Зарегистрироваться» неактивна

  @TC-SHOP-005 @ui @registration @email @validation @negative @p1
  Scenario: Email с пробелами → ошибка «Некорректный email» (Negative)
    # AC2 REQ-REG-002: пробелы в разных позициях не проходят валидацию.
    Given Открыта форма регистрации
    When Пользователь вводит email 'user @example.com' (пробел перед @)
    And Пользователь уводит фокус с поля email или пытается отправить форму
    Then Отображается сообщение об ошибке «Некорректный email»
    And Проверка повторяется для вариантов 'user@ example.com', 'user@example.com ' и ' user@example.com'
    And Во всех вариантах кнопка «Зарегистрироваться» неактивна

  @TC-SHOP-006 @ui @registration @email @validation @boundary @negative @p1 @T412d2d43
  Scenario: Пустое значение email → ошибка, кнопка «Зарегистрироваться» неактивна (Boundary)
    # Ambiguity: поведение при пустом значении не описано в критериях приёмки — требуется уточнение PO.
    Given Открыта форма регистрации, поле email пустое
    When Пользователь не заполняет email и уводит фокус с поля / пытается отправить форму
    Then Отображается ошибка о необходимости корректного email (ожидаемо «Некорректный email»)
    And Кнопка «Зарегистрироваться» неактивна

  @TC-SHOP-007 @ui @registration @email @validation @boundary @negative @p1 @Tce4dfd09
  Scenario: Email с несколькими @ / незавершённые форматы → ошибка «Некорректный email» (Boundary)
    # Ambiguity: точный формат (regex) валидации email не задан — требуется подтверждение PO.
    Given Открыта форма регистрации
    When Пользователь поочерёдно вводит невалидные email: 'user@@example.com', 'user@example', '@example.com', 'user@'
    Then Для каждого варианта отображается ошибка «Некорректный email»
    And Кнопка «Зарегистрироваться» остаётся неактивной
