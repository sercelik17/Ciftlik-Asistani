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

export default function Signup() {
  const router = useRouter();
  const { signUp } = useAuth();

  const [ciftlikAdi, setCiftlikAdi] = useState('');
  const [adSoyad, setAdSoyad] = useState('');
  const [eposta, setEposta] = useState('');
  const [sifre, setSifre] = useState('');
  const [telefon, setTelefon] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [secureTextEntry, setSecureTextEntry] = useState(true);

  const handleSignup = async () => {
    const ciftlikTrimmed = ciftlikAdi.trim();
    const adSoyadTrimmed = adSoyad.trim();
    const emailTrimmed = eposta.trim();
    const passwordTrimmed = sifre.trim();
    const telefonTrimmed = telefon.trim();

    if (!ciftlikTrimmed || !adSoyadTrimmed || !emailTrimmed || !passwordTrimmed) {
      Alert.alert('Hata', 'Lütfen yıldızlı (*) alanları doldurun.');
      return;
    }

    setIsLoading(true);
    try {
      console.log(`Attempting signup to: ${API_URL}/auth/signup`);
      const response = await fetch(`${API_URL}/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ciftlik_adi: ciftlikTrimmed,
          ad_soyad: adSoyadTrimmed,
          eposta: emailTrimmed,
          sifre: passwordTrimmed,
          telefon: telefonTrimmed || null,
        }),
      });

      const data = await response.json();

      if (response.ok && data.access_token) {
        await signUp(data.access_token, {
          ciftlik_id: data.ciftlik_id,
          ad_soyad: adSoyadTrimmed,
          eposta: emailTrimmed,
        });
        // Kayıt olduktan sonra kullanıcı chat (Asistan) ekranına yönlendirilsin
        router.replace('/(tabs)/chat' as any);
      } else {
        Alert.alert('Kayıt Başarısız', data.detail || 'Kayıt oluşturulamadı.');
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
              <MaterialCommunityIcons name="magic-staff" size={40} color="#fff" />
            </View>
            <Text style={styles.appTitle}>Çiftlik Asistanı</Text>
            <Text style={styles.appSubtitle}>Yeni Üyelik Oluşturun</Text>
          </View>

          <View style={styles.cardContainer}>
            <Text style={styles.cardTitle}>Kayıt Ol</Text>

            {/* Farm Name Input */}
            <View style={styles.inputWrapper}>
              <MaterialCommunityIcons name="home-group" size={20} color="#78909C" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Çiftlik Adı *"
                placeholderTextColor="#90A4AE"
                value={ciftlikAdi}
                onChangeText={setCiftlikAdi}
              />
            </View>

            {/* Full Name Input */}
            <View style={styles.inputWrapper}>
              <Ionicons name="person-outline" size={20} color="#78909C" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Ad Soyad *"
                placeholderTextColor="#90A4AE"
                value={adSoyad}
                onChangeText={setAdSoyad}
              />
            </View>

            {/* Email Input */}
            <View style={styles.inputWrapper}>
              <Ionicons name="mail-outline" size={20} color="#78909C" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="E-posta Adresi *"
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
                placeholder="Şifre *"
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

            {/* Phone Number Input */}
            <View style={styles.inputWrapper}>
              <Ionicons name="call-outline" size={20} color="#78909C" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Telefon (İsteğe Bağlı)"
                placeholderTextColor="#90A4AE"
                keyboardType="phone-pad"
                value={telefon}
                onChangeText={setTelefon}
              />
            </View>

            {/* Signup Button */}
            <TouchableOpacity
              style={styles.button}
              onPress={handleSignup}
              disabled={isLoading}
              activeOpacity={0.8}
            >
              {isLoading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>Kayıt Ol</Text>
              )}
            </TouchableOpacity>

            {/* Go to Login */}
            <TouchableOpacity
              style={styles.loginLink}
              onPress={() => router.push('/login' as any)}
              activeOpacity={0.7}
            >
              <Text style={styles.loginText}>
                Zaten hesabınız var mı? <Text style={styles.loginTextHighlight}>Giriş Yapın</Text>
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
    marginBottom: 24,
  },
  logoCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#1B5E20',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#1B5E20',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 8,
    marginBottom: 12,
  },
  appTitle: {
    fontSize: 26,
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
    backgroundColor: '#ffffff',
    borderRadius: 24,
    padding: 24,
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
    marginBottom: 14,
    paddingHorizontal: 16,
    height: 54,
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
    height: 54,
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
  loginLink: {
    alignItems: 'center',
    marginTop: 16,
    padding: 8,
  },
  loginText: {
    color: '#546E7A',
    fontSize: 14,
    fontWeight: '500',
  },
  loginTextHighlight: {
    color: '#1B5E20',
    fontWeight: '700',
  },
});
