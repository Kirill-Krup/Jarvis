import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import sounddevice as sd
from typing import Optional, Tuple, List, Dict


class AudioDeviceManager:

    def __init__(self):
        self._devices = sd.query_devices()
        self._current_input_device: Optional[int] = None
        self._current_output_device: Optional[int] = None

    def get_all_devices(self) -> List[Dict]:
        devices = []
        for i, dev in enumerate(self._devices):
            devices.append({
                'index': i,
                'name': dev['name'],
                'max_input_channels': dev['max_input_channels'],
                'max_output_channels': dev['max_output_channels'],
                'is_input': dev['max_input_channels'] > 0,
                'is_output': dev['max_output_channels'] > 0
            })
        return devices

    def get_default_output_device(self) -> Optional[Dict]:
        try:
            default_output = sd.default.device[1]
            if isinstance(default_output, int):
                return self._devices[default_output]
            return sd.query_devices(default_output)
        except Exception as e:
            print(f"[WARN] Не удалось получить устройство вывода: {e}")
            return None

    def get_default_input_device(self) -> Optional[Dict]:
        try:
            default_input = sd.default.device[0]
            if isinstance(default_input, int):
                return self._devices[default_input]
            return sd.query_devices(default_input)
        except Exception as e:
            print(f"[WARN] Не удалось получить устройство ввода: {e}")
            return None

    def find_matching_input_device(self, output_device: Dict) -> Optional[int]:
        if not output_device:
            return None

        output_name = output_device.get('name', '').lower()

        for i, dev in enumerate(self._devices):
            if dev['max_input_channels'] > 0:
                dev_name = dev.get('name', '').lower()
                if dev_name == output_name:
                    print(f"[MIC] Найден соответствующий микрофон: {dev.get('name')} (индекс {i})")
                    return i

        bluetooth_keywords = ['hands-free', 'ag audio', 'bluetooth', 'headset']
        for keyword in bluetooth_keywords:
            if keyword in output_name:
                for i, dev in enumerate(self._devices):
                    if dev['max_input_channels'] > 0 and keyword in dev.get('name', '').lower():
                        print(f"[MIC] Найден микрофон Bluetooth гарнитуры: {dev.get('name')} (индекс {i})")
                        return i

        return None

    def get_best_input_device(self) -> int:

        print("\n🎧 Определение устройства записи...")

        output_device = self.get_default_output_device()
        if output_device:
            print(f"   Устройство вывода: {output_device.get('name')}")
            matched_input = self.find_matching_input_device(output_device)
            if matched_input is not None:
                self._current_input_device = matched_input
                return matched_input

        default_input = self.get_default_input_device()
        if default_input:
            print(f"   Использую системный микрофон: {default_input.get('name')}")
            self._current_input_device = sd.default.device[0]
            return self._current_input_device

        for i, dev in enumerate(self._devices):
            if dev['max_input_channels'] > 0:
                print(f"   Использую первое доступное устройство: {dev.get('name')} (индекс {i})")
                self._current_input_device = i
                return i

        raise RuntimeError("❌ Не найдено ни одного устройства ввода (микрофона)!")

    def set_custom_input_device(self, device_index: int) -> bool:
        if 0 <= device_index < len(self._devices):
            if self._devices[device_index]['max_input_channels'] > 0:
                self._current_input_device = device_index
                print(f"[OK] Установлен микрофон: {self._devices[device_index]['name']} (индекс {device_index})")
                return True
            else:
                print(f"❌ Устройство {device_index} не поддерживает запись звука")
                return False
        print(f"❌ Устройства с индексом {device_index} не существует")
        return False

    def get_current_input_device(self) -> int:
        if self._current_input_device is None:
            self._current_input_device = self.get_best_input_device()
        return self._current_input_device

    def print_devices_status(self):
        print("\n" + "=" * 60)
        print("📋 ДОСТУПНЫЕ АУДИОУСТРОЙСТВА")
        print("=" * 60)
        print(f"{'Индекс':<6} {'Тип':<12} {'Имя устройства'}")
        print("-" * 60)

        for i, dev in enumerate(self._devices):
            dev_type = []
            if dev['max_input_channels'] > 0:
                dev_type.append("[MIC] ВВОД")
            if dev['max_output_channels'] > 0:
                dev_type.append("🔊 ВЫВОД")

            type_str = ", ".join(dev_type)
            print(f"{i:<6} {type_str:<12} {dev['name']}")

        print("-" * 60)

        try:
            default_input = self.get_default_input_device()
            default_output = self.get_default_output_device()
            if default_input:
                print(f"[MIC] Системный микрофон по умолчанию: {default_input.get('name')}")
            if default_output:
                print(f"🔊 Системный динамик по умолчанию: {default_output.get('name')}")
        except:
            pass

        if self._current_input_device is not None:
            print(f"[OK] Текущий выбранный микрофон: {self._devices[self._current_input_device]['name']}")

        print("=" * 60 + "\n")