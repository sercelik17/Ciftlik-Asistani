import { Platform } from 'react-native';

// Intercept and downgrade the expo-notifications Expo Go warning to a regular console.warn
// to prevent the full-screen RedBox error on Android in development mode.
if (__DEV__) {
  const originalConsoleError = console.error;
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('expo-notifications: Android Push notifications') ||
       args[0].includes('Android Push notifications'))
    ) {
      console.warn(...args);
      return;
    }
    originalConsoleError(...args);
  };
}

