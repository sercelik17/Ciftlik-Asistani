import './patch-console';
import React, { useEffect } from 'react';
import { Platform, View, ActivityIndicator } from 'react-native';
import { Stack, router, useSegments } from "expo-router";
import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { AuthProvider, useAuth } from '../context/AuthContext';

// Uygulama açıkken (foreground) bildirimlerin nasıl davranacağını belirle
if (Platform.OS !== 'web') {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
      shouldShowBanner: true,
      shouldShowList: true,
    }),
  });
}

async function registerForPushNotificationsAsync() {
 if (Platform.OS === 'web') {
    console.log('Web ortamında push notification devre dışı.');
    return null;
  }

  if (!Device.isDevice) {
    console.log('Push bildirimleri emülatörde test edilemez. Lütfen gerçek bir cihaz kullanın.');
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
      console.log('✅ Android bildirim kanalı oluşturuldu.');
    } catch (e) {
      console.log('❌ Android bildirim kanalı oluşturulamadı:', e);
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
      console.log('❌ Push bildirim izni alınamadı! Status:', finalStatus);
      return null;
    }
    
    console.log('✅ Push bildirim izni verildi.');
  } catch (e) {
    console.log('❌ İzin kontrolü sırasında hata:', e);
    return null;
  }

  try {
    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ??
      Constants.easConfig?.projectId;
      
    if (!projectId) {
      console.log('❌ Project ID app.json içinde bulunamadı. EAS projectId kontrol edin.');
      return null;
    }

    console.log('🔑 Project ID bulundu:', projectId);
    
    const tokenData = await Notifications.getExpoPushTokenAsync({ projectId });
    token = tokenData.data;
    console.log('✅ Expo Push Token alındı:', token);
  } catch (error) {
    console.log('❌ Expo Push Token alınırken hata:', error);
    try {
      token = (await Notifications.getDevicePushTokenAsync()).data;
      console.log('✅ Cihaz push token (fall back) alındı:', token);
    } catch (fallbackError) {
      console.log('❌ Cihaz push token da alınamadı:', fallbackError);
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

  // PWA Desteği için Service Worker Kayıt İşlemi (Sadece Web platformunda çalışır)
  useEffect(() => {
    if (Platform.OS === 'web' && 'serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
          .then((registration) => {
            console.log('✅ PWA: Service Worker başarıyla kaydedildi:', registration.scope);
          })
          .catch((error) => {
            console.log('❌ PWA: Service Worker kaydı başarısız:', error);
          });
      });
    }
  }, []);

  // 1. Kimlik Doğrulama Yönlendirme Koruması (Route Guarding)
  useEffect(() => {
    if (isLoading) return;

    const firstSegment = segments[0] as string | undefined;
    const inAuthGroup = firstSegment === 'login' || firstSegment === 'signup';

    if (!token && !inAuthGroup) {
      // Token yoksa ve kullanıcı login/signup sayfasında değilse login'e at
      router.replace('/login' as any);
    } else if (token && inAuthGroup) {
      // Token varsa ve login/signup sayfasındaysa chat ekranına yönlendir
      router.replace('/(tabs)/chat' as any);
    }
  }, [token, isLoading, segments]);

  // 2. Bildirimler ve Push Token Kayıt İşlemleri
  useEffect(() => {
    // Sadece kullanıcı giriş yapmışsa push token'ı kaydet
    if (!token) return;

    if (Platform.OS === 'web') {
  console.log('Web ortamında bildirim dinleyicileri devre dışı.');
  return;
    }

    registerForPushNotificationsAsync().then(pushToken => {
      if (!pushToken) {
        console.log('⚠️ Token alınamadı, backend kayıt atlandı.');
        return;
      }

      // API URL'ini IP adresine göre bul
      const hostUri = Constants.expoConfig?.hostUri;
      const ip = hostUri ? hostUri.split(':')[0] : 'localhost';
      const API_URL = `http://${ip}:8001`;

      console.log("📡 Token backend'e kaydediliyor:", API_URL);

      fetch(`${API_URL}/register-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`, // Kullanıcı tokenını ekle
        },
        body: JSON.stringify({ token: pushToken }),
      })
      .then(res => res.json())
      .then(data => console.log('✅ Push Token Backend Kayıt Başarılı:', data))
      .catch(err => console.log('❌ Push Token Backend Kayıt Hatası:', err));
    });

    // 1. Uygulama kapalıyken (cold start) bildirime tıklanıp açıldığında yönlendirme yap
    Notifications.getLastNotificationResponseAsync().then(response => {
      if (response && response.actionIdentifier === Notifications.DEFAULT_ACTION_IDENTIFIER) {
        console.log('🔔 Cold start: Bildirime tıklanarak açıldı.');
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
        }, 1000); // Expo Router navigation context'in hazır olması için bekleme süresi
      }
    });

    // 2. Uygulama açıkken (foreground / background) bildirime tıklandığında yönlendirme yap
    const subscription = Notifications.addNotificationResponseReceivedListener(response => {
      console.log('🔔 Bildirime tıklandı. Yönlendiriliyor...');
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

