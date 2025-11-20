### Стерерть прошивку ###
```python -m esptool --port COM5 erase_flas```

### Загрузить прошивку ###
```python -m esptool --chip esp32 --port COM5 --baud 460800 write_flash -z 0x1000 firmware.bin```
