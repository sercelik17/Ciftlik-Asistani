import './patch-console';
import React, { useEffect } from 'react';
import { Platform, View, ActivityIndicator } from 'react-native';
import { Stack, router, useSegments } from "expo-router";
import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { AuthProvider, useAuth } from '../context/AuthContext';

// Uygulama aÃ§Ä±kken (foreground) bildirimlerin nasÄ±l davranacaÄŸÄ±nÄ± belirle
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

async function registerForPushNotificationsAsync() {
  if (!Device.isDevice) {
    console.log('Push bildirimleri emÃ¼latÃ¶rde test edilemez. LÃ¼tfen gerÃ§ek bir cihaz kullanÄ±n.');
    return null;
  }

  let token: string | null = null;

  if (Platform.OS === 'android') {
    try {
      await Notifications.setNotificationChannelAsync('default', {
        name: 'default',
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: '#FF231F7C',
        sound: 'default',
        enableVibrate: true,
        showBadge: true,
      });
      console.log('âœ… Android bildirim kanalÄ± oluÅŸturuldu.');
    } catch (e) {
      console.log('âŒ Android bildirim kanalÄ± oluÅŸturulamadÄ±:', e);
    }
  }

  try {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    
    if (finalStatus !== 'granted') {
      console.log('âŒ Push bildirim izni alÄ±namadÄ±! Status:', finalStatus);
      return null;
    }
    
    console.log('âœ… Push bildirim izni verildi.');
  } catch (e) {
    console.log('âŒ Ä°zin kontrolÃ¼ sÄ±rasÄ±nda hata:', e);
    return null;
  }

  try {
    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ??
      Constants.easConfig?.projectId;
      
    if (!projectId) {
      console.log('âŒ Project ID app.json iÃ§inde bulunamadÄ±. EAS projectId kontrol edin.');
      return null;
    }

    console.log('ğŸ”‘ Project ID bulundu:', projectId);
    
    const tokenData = await Notifications.getExpoPushTokenAsync({ projectId });
    token = tokenData.data;
    console.log('âœ… Expo Push Token alÄ±ndÄ±:', token);
  } catch (error) {
    console.log('âŒ Expo Push Token alÄ±nÄ±rken hata:', error);
    try {
      token = (await Notifications.getDevicePushTokenAsync()).data;
      console.log('âœ… Cihaz push token (fall back) alÄ±ndÄ±:', token);
    } catch (fallbackError) {
      console.log('âŒ Cihaz push token da alÄ±namadÄ±:', fallbackError);
    }
    return token;
  }

  return token;
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <RootLayoutNav />
    </AuthProvider>
  );
}

function RootLayoutNav() {
  const { token, isLoading } = useAuth();
  const segments = useSegments();

  // PWA DesteÄŸi iÃ§in Service Worker KayÄ±t Ä°ÅŸlemi (Sadece Web platformunda Ã§alÄ±ÅŸÄ±r)
  useEffect(() => {
    if (Platform.OS === 'web' && 'serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
          .then((registration) => {
            console.log('âœ… PWA: Service Worker baÅŸarÄ±yla kaydedildi:', registration.scope);
          })
          .catch((error) => {
            console.log('âŒ PWA: Service Worker kaydÄ± baÅŸarÄ±sÄ±z:', error);
          });
      });
    }
  }, []);

  // 1. Kimlik DoÄŸrulama YÃ¶nlendirme KorumasÄ± (Route Guarding)
  useEffect(() => {
    if (isLoading) return;

    const firstSegment = segments[0] as string | undefined;
    const inAuthGroup = firstSegment === 'login' || firstSegment === 'signup';

    if (!token && !inAuthGroup) {
      // Token yoksa ve kullanÄ±cÄ± login/signup sayfasÄ±nda deÄŸilse login'e at
      router.replace('/login' as any);
    } else if (token && inAuthGroup) {
      // Token varsa ve login/signup sayfasÄ±ndaysa chat ekranÄ±na yÃ¶nlendir
      router.replace('/(tabs)/chat' as any);
    }
  }, [token, isLoading, segments]);

  // 2. Bildirimler ve Push Token KayÄ±t Ä°ÅŸlemleri
  useEffect(() => {
    // Sadece kullanÄ±cÄ± giriÅŸ yapmÄ±ÅŸsa push token'Ä± kaydet
    if (!token) return;

    registerForPushNotificationsAsync().then(pushToken => {
      if (!pushToken) {
        console.log('âš ï¸ Token alÄ±namadÄ±, backend kayÄ±t atlandÄ±.');
        return;
      }

      // API URL'ini IP adresine gÃ¶re bul
      const hostUri = Constants.expoConfig?.hostUri;
      const ip = hostUri ? hostUri.split(':')[0] : 'localhost';
      const API_URL = `http://${ip}:8001`;

      console.log("ğŸ“¡ Token backend'e kaydediliyor:", API_URL);

      fetch(`${API_URL}/register-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`, // KullanÄ±cÄ± tokenÄ±nÄ± ekle
        },
        body: JSON.stringify({ token: pushToken }),
      })
      .then(res => res.json())
      .then(data => console.log('âœ… Push Token Backend KayÄ±t BaÅŸarÄ±lÄ±:', data))
      .catch(err => console.log('âŒ Push Token Backend KayÄ±t HatasÄ±:', err));
    });

    // 1. Uygulama kapalÄ±yken (cold start) bildirime tÄ±klanÄ±p aÃ§Ä±ldÄ±ÄŸÄ±nda yÃ¶nlendirme yap
    Notifications.getLastNotificationResponseAsync().then(response => {
      if (response && response.actionIdentifier === Notifications.DEFAULT_ACTION_IDENTIFIER) {
        console.log('ğŸ”” Cold start: Bildirime tÄ±klanarak aÃ§Ä±ldÄ±.');
        const notificationData = response.notification.request.content.data;
        const highlightCow = notificationData?.highlight_cow as string | undefined;
        const alertMsg = notificationData?.alert_msg as string | undefined;

        setTimeout(() => {
          if (highlightCow || alertMsg) {
            router.push({
              pathname: '/',
              params: { highlight_cow: highlightCow, alert_msg: alertMsg }
            });
          } else {
            router.push('/');
          }
        }, 1000); // Expo Router navigation context'in hazÄ±r olmasÄ± iÃ§in bekleme sÃ¼resi
      }
    });

    // 2. Uygulama aÃ§Ä±kken (foreground / background) bildirime tÄ±klandÄ±ÄŸÄ±nda yÃ¶nlendirme yap
    const subscription = Notifications.addNotificationResponseReceivedListener(response => {
      console.log('ğŸ”” Bildirime tÄ±klandÄ±. YÃ¶nlendiriliyor...');
      const notificationData = response.notification.request.content.data;
      const highlightCow = notificationData?.highlight_cow as string | undefined;
      const alertMsg = notificationData?.alert_msg as string | undefined;

      if (highlightCow || alertMsg) {
        router.push({
          pathname: '/',
          params: { highlight_cow: highlightCow, alert_msg: alertMsg }
        });
      } else {
        router.push('/');
      }
    });

    return () => {
      subscription.remove();
    };
  }, [token]);

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F4F7F6' }}>
        <ActivityIndicator size="large" color="#1B5E20" />
      </View>
    );
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="login" />
      <Stack.Screen name="signup" />
      <Stack.Screen name="(tabs)" />
    </Stack>
  );
}


