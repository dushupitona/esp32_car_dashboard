### Слушать порт ###
```mpremote connect COM5```

### Остановить main ###
``` ctrl + C ```

### Загрузить файл ###
```mpremote connect COM5 fs put main.py```

### Посмотреть все файлы ###
```mpremote connect COM5 fs ls```


```
(venv) PS C:\Users\vstas\OneDrive\Рабочий стол\7sem\esp32_car_dashboard> ampy --port COM7 ls
/boot.py
/test.txt
(venv) PS C:\Users\vstas\OneDrive\Рабочий стол\7sem\esp32_car_dashboard> cd core
(venv) PS C:\Users\vstas\OneDrive\Рабочий стол\7sem\esp32_car_dashboard\core> ampy --port COM7 put main.py
(venv) PS C:\Users\vstas\OneDrive\Рабочий стол\7sem\esp32_car_dashboard\core> ampy --port COM7 ls
/boot.py
/main.py
/test.txt
(venv) PS C:\Users\vstas\OneDrive\Рабочий стол\7sem\esp32_car_dashboard\core> mpremote connect COM7
```