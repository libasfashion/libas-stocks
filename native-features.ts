// native-features.ts
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { Filesystem, Directory } from '@capacitor/filesystem';
import { Media } from '@capacitor-community/media';
import { Contacts } from '@capacitor-community/contacts';
import { Capacitor } from '@capacitor/core';

/**
 * Request camera (and microphone if recording) permissions and take a photo.
 */
export async function takePhotoAndSave() {
  // 1) Request camera permission (Camera plugin helper)
  try {
    // Camera.requestPermissions() usually returns an object indicating granted status
    // If your plugin version uses a different helper, use that plugin's README.
    await Camera.requestPermissions(); // prompts user
  } catch (err) {
    // fallback: user denied or plugin doesn't expose helper; we'll try to continue
    console.warn('Camera permission request failed or not exposed by plugin:', err);
  }

  // 2) Take photo
  const photo = await Camera.getPhoto({
    quality: 80,
    allowEditing: false,
    resultType: CameraResultType.Uri,
    source: CameraSource.Camera
  });

  // 3) Convert to base64 to save with Filesystem
  const webPath = photo.webPath ?? photo.path;
  if (!webPath) throw new Error('No photo path returned');

  // fetch file then convert to base64
  const response = await fetch(webPath);
  const blob = await response.blob();
  const base64Data = await blobToBase64(blob);

  // 4) Write file into app data directory
  const fileName = `photo-${Date.now()}.jpeg`;
  await Filesystem.writeFile({
    path: `photos/${fileName}`,
    data: base64Data,
    directory: Directory.Data
  });

  // 5) Optionally add to system gallery via @capacitor-community/media (if installed)
  try {
    // media.save returns info after saving to gallery / media store on Android
    const saveResult = await Media.save({
      body: {
        fileName,
        base64Data,
        album: 'Libas',       // optional album name
        // type: 'image'        // some versions accept explicit type
      }
    });
    console.log('Saved to gallery:', saveResult);
  } catch (e) {
    console.warn('Failed adding to gallery via Media plugin (may still be in app data):', e);
  }

  return { savedFile: fileName };
}

/** helper to convert Blob to base64 string (without data:* prefix) */
function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = reject;
    reader.onload = () => {
      const dataUrl = reader.result as string;
      resolve(dataUrl.split(',')[1]); // strip `data:*/*;base64,`
    };
    reader.readAsDataURL(blob);
  });
}

/**
 * Request & read contacts
 */
export async function readContactsSafe() {
  // Request contacts permission
  try {
    await Contacts.requestPermissions();
  } catch (err) {
    console.warn('Contacts permission request failed:', err);
  }

  // After permission, fetch contacts (pageSize optional)
  const result = await Contacts.getContacts({ pageSize: 200 });
  // result.contacts is an array (plugin-specific shape)
  return result.contacts ?? [];
}

/**
 * Request media (gallery) permissions for Android 13+ and fallback
 * Explanation: Android 13 introduced READ_MEDIA_* permissions for images/video/audio.
 * Plugin may provide helper; use plugin.requestPermissions if available.
 */
export async function requestMediaPermissions() {
  try {
    // Some community media plugin versions provide requestPermissions
    if (typeof (Media as any).requestPermissions === 'function') {
      await (Media as any).requestPermissions();
      return;
    }
  } catch (err) {
    console.warn('Media plugin requestPermissions error:', err);
  }

  // If plugin does not expose helper, the native AndroidManifest has the uses-permission entries
  // and the WebView / plugin will prompt automatically when the feature is used.
  return;
}
