import type { PickedPhoto } from '@/api/client';

// iPhone-Fotos (.heic) ausdrücklich erlauben: Windows kennt den Typ oft nicht und blendet
// sie bei „image/*“ sonst aus. Umgewandelt wird im Backend.
const ACCEPT = 'image/*,.heic,.heif';

/**
 * Dateiauswahl im Browser. Anders als der Expo-Bildwähler öffnet sie das Bild nicht selbst,
 * daher funktionieren auch Formate, die der Browser nicht anzeigen kann (HEIC).
 * Gibt null zurück, wenn nichts gewählt wurde.
 */
export function pickPhotoWeb(): Promise<PickedPhoto | null> {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = ACCEPT;
    input.style.display = 'none';
    const done = (photo: PickedPhoto | null) => {
      input.remove();
      resolve(photo);
    };
    input.addEventListener('change', () => {
      const file = input.files?.[0];
      done(
        file
          ? { uri: URL.createObjectURL(file), name: file.name, mimeType: file.type || 'application/octet-stream', webFile: file }
          : null,
      );
    });
    input.addEventListener('cancel', () => done(null));
    document.body.appendChild(input);
    input.click();
  });
}
