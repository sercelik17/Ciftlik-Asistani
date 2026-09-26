import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Constants from 'expo-constants';
import { useAuth } from '../context/AuthContext';

const getApiUrl = () => {
  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) return `http://${hostUri.split(':')[0]}:8001`;
  return `http://localhost:8001`;
};

const API_URL = getApiUrl();

export default function Login() {
  const router = useRouter();
  const { signIn } = useAuth();

  const [eposta, setEposta] = useState('');
  const [sifre, setSifre] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [secureTextEntry, setSecureTextEntry] = useState(true);

  const handleLogin = async () => {
    const emailTrimmed = eposta.trim();
    const passwordTrimmed = sifre.trim();

    if (!emailTrimmed || !passwordTrimmed) {
      Alert.alert('Hata', 'Lütfen tüm alanları doldurun.');
      return;
    }

    setIsLoading(true);
    try {
      console.log(`Attempting login to: ${API_URL}/auth/login`);
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          eposta: emailTrimmed,
          sifre: passwordTrimmed,
        }),
      });

      const data = await response.json();

      if (response.ok && data.access_token) {
        await signIn(data.access_token, {
          ciftlik_id: data.ciftlik_id,
          ad_soyad: data.ad_soyad,
          eposta: emailTrimmed,
        });
        // Giriş yaptıktan sonra kullanıcı chat (Asistan) ekranına yönlendirilsin
        router.replace('/(tabs)/chat' as any);
      } else {
        Alert.alert('Giriş Başarısız', data.detail || 'E-posta veya şifre hatalı.');
      }
    } catch (error) {
      console.error(error);
      Alert.alert('Bağlantı Hatası', 'Sunucuya bağlanılamadı. Lütfen internet bağlantınızı ve sunucuyu kontrol edin.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
          <View style={styles.headerContainer}>
            <View style={styles.logoCircle}>
              <MaterialCommunityIcons name="magic-staff" size={48} color="#fff" />
            </View>
            <Text style={styles.appTitle}>Çiftlik Asistanı</Text>
            <Text style={styles.appSubtitle}>Yapay Zekâ Destekli Süt Sığırcılığı Karar Destek Sistemi</Text>
          </View>

          <View style={styles.cardContainer}>
            <Text style={styles.cardTitle}>Giriş Yap</Text>

            {/* Email Input */}
            <View style={styles.inputWrapper}>
              <Ionicons name="mail-outline" size={20} color="#78909C" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="E-posta Adresiniz"
                placeholderTextColor="#90A4AE"
                keyboardType="email-address"
                autoCapitalize="none"
                value={eposta}
                onChangeText={setEposta}
              />
            </View>

            {/* Password Input */}
            <View style={styles.inputWrapper}>
              <Ionicons name="lock-closed-outline" size={20} color="#78909C" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Şifreniz"
                placeholderTextColor="#90A4AE"
                secureTextEntry={secureTextEntry}
                autoCapitalize="none"
                value={sifre}
                onChangeText={setSifre}
              />
              <TouchableOpacity
                onPress={() => setSecureTextEntry(!secureTextEntry)}
                style={styles.eyeIcon}
              >
                <Ionicons
                  name={secureTextEntry ? 'eye-off-outline' : 'eye-outline'}
                  size={20}
                  color="#78909C"
                />
              </TouchableOpacity>
            </View>

            {/* Login Button */}
            <TouchableOpacity
              style={styles.button}
              onPress={handleLogin}
              disabled={isLoading}
              activeOpacity={0.8}
            >
              {isLoading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>Giriş Yap</Text>
              )}
            </TouchableOpacity>

            {/* Go to Signup */}
            <TouchableOpacity
              style={styles.signupLink}
              onPress={() => router.push('/signup' as any)}
              activeOpacity={0.7}
            >
              <Text style={styles.signupText}>
                Yeni misiniz? <Text style={styles.signupTextHighlight}>Kayıt Olun</Text>
              </Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F4F7F6',
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  headerContainer: {
    alignItems: 'center',
    marginBottom: 32,
  },
  logoCircle: {
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: '#1B5E20',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#1B5E20',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 8,
    marginBottom: 16,
  },
  appTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: '#1B5E20',
    letterSpacing: 0.5,
  },
  appSubtitle: {
    fontSize: 14,
    color: '#546E7A',
    marginTop: 4,
    fontWeight: '500',
  },
  cardContainer: {
    width: '100%',
    maxWidth: 600,
    alignSelf: 'center',
    backgroundColor: '#ffffff',
    borderRadius: 24,
    padding: 28,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.05,
    shadowRadius: 15,
    elevation: 4,
  },
  cardTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#37474F',
    marginBottom: 20,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F8FAF9',
    borderWidth: 1,
    borderColor: '#ECEFF1',
    borderRadius: 14,
    marginBottom: 16,
    paddingHorizontal: 16,
    height: 56,
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    color: '#37474F',
    fontSize: 16,
    height: '100%',
  },
  eyeIcon: {
    padding: 8,
  },
  button: {
    backgroundColor: '#1B5E20',
    borderRadius: 14,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
    shadowColor: '#1B5E20',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  signupLink: {
    alignItems: 'center',
    marginTop: 20,
    padding: 8,
  },
  signupText: {
    color: '#546E7A',
    fontSize: 14,
    fontWeight: '500',
  },
  signupTextHighlight: {
    color: '#1B5E20',
    fontWeight: '700',
  },
});
