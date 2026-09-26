import React, { useEffect, useRef, useState } from 'react';
import EventSource from 'react-native-sse';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  Keyboard,
  ScrollView,
  StatusBar,
} from 'react-native';
import Markdown, { RenderRules } from 'react-native-markdown-display';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import { StepIndicator } from '../../components/StepIndicator';
import Constants from 'expo-constants';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAuth } from '../../context/AuthContext';

interface Message {
  id: string;
  text: string;
  spokenText?: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  isStreaming?: boolean; // SSE akışı devam ediyor mu?
  step?: string;         // Backend'den gelen anlık adım bildirimi
}

// ZİL MÖNÜSÜ İÇİN ALARM ARAYÜZÜ
interface Alarm {
  id: number;
  kupe_no: string;
  isim: string;
  tarih: string;
  sagim_zamani: string;
  dusus_yuzdesi: number;
  mesaj: string;
}

const getApiUrl = () => {
  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) {
    const ip = hostUri.split(':')[0];
    return `http://${ip}:8001`;
  }
  return `http://localhost:8001`;
};

const API_URL = getApiUrl();
const SHORTCUTS = [
  { label: 'Merhaba', query: 'Merhaba' },
  { label: '⚠️ Riskliler (Düşüş Olanlar)', query: 'Süt veriminde düşüş yaşayan riskli inekleri listele' },
  { label: '🥛 Bugünkü Toplam Süt', query: 'Bugün sağılan toplam süt miktarı kaç litre?' },
  { label: "Süt verimi en yüksek inekler", query: 'Süt verimi en yüksek olan 10 ineği getir' },
  { label: '📊 Sürü Ortalaması', query: 'Çiftliğin genel sürü süt ortalaması kaç litredir?' },
];

const markdownRules: RenderRules = {
  table: (node, children, parent, styles) => (
    <ScrollView
      key={node.key}
      horizontal={true}
      showsHorizontalScrollIndicator={false}
      style={styles.tableScrollView}
      contentContainerStyle={styles.tableContent}
    >
      <View style={styles.tableCard}>
        {children}
      </View>
    </ScrollView>
  ),
  tr: (node, children, parent, styles) => (
    <View key={node.key} style={styles.tr}>
      {children}
    </View>
  ),
  th: (node, children, parent, styles) => (
    <View key={node.key} style={styles.th}>
      <Text style={styles.thText}>{children}</Text>
    </View>
  ),
  td: (node, children, parent, styles) => (
    <View key={node.key} style={styles.td}>
      <Text style={styles.tdText}>{children}</Text>
    </View>
  ),
};

export default function Chat() {
  const router = useRouter();
  const { token } = useAuth();
  const params = useLocalSearchParams();
  const queryParam = params.query;

  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);

  // AKIŞ VE İŞLEM DURUMLARI
  const [isLoading, setIsLoading] = useState(false);
  const activeEventSourceRef = useRef<EventSource | null>(null);

  // SES DURUMLARI
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string>('Sorunuz analiz ediliyor...');

  // YENİ: ZİL VE ALARM STATE'LERİ
  const [unreadAlarms, setUnreadAlarms] = useState<Alarm[]>([]);
  const [isBellOpen, setIsBellOpen] = useState(false);

  const soundRef = useRef<Audio.Sound | null>(null);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    if (queryParam && typeof queryParam === 'string') {
      sendMessage(queryParam);
      router.setParams({ query: undefined });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryParam]);

  useEffect(() => {
    (async () => {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') console.log('Mikrofon izni yok');
    })();
    return () => {
      soundRef.current?.unloadAsync();
      if (activeEventSourceRef.current) {
        activeEventSourceRef.current.close();
      }
    };
  }, []);

  // OKUNMAMIŞ ALARMLARI ÇEK (7/24 Gözcü Bağlantısı)
  const fetchUnreadAlarms = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/alarms?unread_only=true`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) setUnreadAlarms(data.alarms || []);
      }
    } catch {
      // Alarm çekme hatası
    }
  };

  useEffect(() => {
    fetchUnreadAlarms();
    const interval = setInterval(fetchUnreadAlarms, 20000);
    return () => clearInterval(interval);
  }, []);

  // ALARMA TIKLANDIĞINDA ÖZETLER KARTINA AKTAR (AHTAPOT SICRAMASI)
  const handleAlarmClick = (alarm: Alarm) => {
    setIsBellOpen(false);
    // Özetler sekmesine zıpla ve parametre olarak alarm bilgisini ilet
    router.push({
      pathname: '/',
      params: { highlight_cow: alarm.kupe_no, alert_msg: alarm.mesaj }
    });
  };

  const speakText = async (messageId: string, text: string) => {
    if (!text || !text.trim()) return;
    if (speakingId === messageId) {
      await soundRef.current?.stopAsync();
      await soundRef.current?.unloadAsync();
      soundRef.current = null;
      setSpeakingId(null);
      return;
    }
    if (soundRef.current) {
      await soundRef.current.stopAsync();
      await soundRef.current.unloadAsync();
      soundRef.current = null;
    }
    try {
      setSpeakingId(messageId);
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });
      const ttsUrl = `${API_URL}/tts?text=${encodeURIComponent(text)}`;
      const { sound } = await Audio.Sound.createAsync(
        { uri: ttsUrl, headers: { 'Authorization': `Bearer ${token}` } },
        { shouldPlay: true }
      );
      soundRef.current = sound;
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          setSpeakingId(null);
          sound.unloadAsync();
          soundRef.current = null;
        }
      });
    } catch (err) {
      setSpeakingId(null);
    }
  };

  // İŞLEMİ GERİ ALMA / İPTAL ETME (ABORT SSE)
  const handleCancelStreaming = () => {
    if (activeEventSourceRef.current) {
      activeEventSourceRef.current.close();
      activeEventSourceRef.current = null;
    }
    setIsLoading(false);

    // Son eklenen bekleyen/streaming bot mesajını iptal edildi olarak güncelle
    setMessages((prev) =>
      prev.map((msg, index) =>
        index === prev.length - 1 && msg.sender === 'bot' && msg.isStreaming
          ? { ...msg, text: "⚠️ *İşlem kullanıcı tarafından durduruldu.*", isStreaming: false, step: undefined }
          : msg
      )
    );
  };

const sendMessage = async (textOverride?: string | any) => {
  const finalQuery = (
    typeof textOverride === 'string' ? textOverride : inputText
  ).trim();

  if (!finalQuery || isLoading) return;

  const userMsgId = `user-${Date.now()}`;
  const botMsgId = `bot-${Date.now() + 1}`;

  setMessages((prev) => [
    ...prev,
    {
      id: userMsgId,
      text: finalQuery,
      sender: 'user',
      timestamp: new Date(),
    },
    {
      id: botMsgId,
      text: '',
      sender: 'bot',
      timestamp: new Date(),
      isStreaming: true,
      step: 'Sorunuz analiz ediliyor...',
    },
  ]);

  if (typeof textOverride !== 'string') {
    setInputText('');
  }

  setIsLoading(true);
  setCurrentStep('Sorunuz analiz ediliyor...');

  const startTime = Date.now();

  try {
    const response = await fetch(`${API_URL}/query/thesis/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        question: finalQuery,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Sunucu hatası (${response.status}): ${errorText}`
      );
    }

    const data = await response.json();

    const duration = ((Date.now() - startTime) / 1000).toFixed(1);

    let sourceText = '';

    if (Array.isArray(data.sources) && data.sources.length > 0) {
      sourceText =
        '\n\n**Kaynaklar:**\n' +
        data.sources
          .map((source: any) => {
            const page =
              source.page !== null &&
              source.page !== undefined
                ? `, s. ${source.page}`
                : '';

            return `- [${source.id}] ${source.title}${page}`;
          })
          .join('\n');
    }

    const finalAnswer =
      `${data.answer || 'Yanıt oluşturulamadı.'}` +
      sourceText +
      `\n\n*⏱️ Yanıt süresi: ${duration} saniye*`;

    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === botMsgId
          ? {
              ...msg,
              text: finalAnswer,
              spokenText: data.answer,
              isStreaming: false,
              step: undefined,
            }
          : msg
      )
    );
  } catch (error) {
    console.error('Tez RAG sorgu hatası:', error);

    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === botMsgId
          ? {
              ...msg,
              text: '❌ Yanıt alınırken bir bağlantı hatası oluştu.',
              isStreaming: false,
              step: undefined,
            }
          : msg
      )
    );
  } finally {
    setIsLoading(false);
    setCurrentStep('');
  }
};

  const startRecording = async () => {
    try {
      Keyboard.dismiss();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: newRecording } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      setRecording(newRecording);
      setIsRecording(true);
    } catch (err) { }
  };

  const stopRecording = async () => {
    if (!recording) return;
    try {
      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      const uri = recording.getURI();
      if (uri) await sendVoiceMessage(uri);
      setRecording(null);
    } catch (err) { }
  };

  const sendVoiceMessage = async (audioUri: string) => {
    setIsLoading(true);
    setCurrentStep('Ses dosyası yükleniyor...');
    const startTime = Date.now();
    try {
      const formData = new FormData();
      formData.append('audio', { uri: audioUri, type: 'audio/m4a', name: 'recording.m4a' } as any);
      const transcribeResponse = await fetch(`${API_URL}/transcribe`, { 
        method: 'POST', 
        body: formData, 
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        } 
      });
      const transcribeData = await transcribeResponse.json();
      const userText = transcribeData.transcription || transcribeData.text;
      if (!userText) throw new Error('Ses anlaşılamadı');

      const userMsgId = `user-${Date.now()}`;
      const botMsgId = `bot-${Date.now() + 1}`;

      setMessages((prev) => [
        ...prev,
        { id: userMsgId, text: userText, sender: 'user', timestamp: new Date() },
        { id: botMsgId, text: '', sender: 'bot', timestamp: new Date(), isStreaming: true, step: 'Sorunuz analiz ediliyor...' }
      ]);

      setCurrentStep('Sorunuz analiz ediliyor...');
      const es = new EventSource(`${API_URL}/query/tool/stream`, { 
        method: 'POST', 
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }, 
        body: JSON.stringify({ question: userText }) 
      });
      activeEventSourceRef.current = es;

      es.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data ?? '{}');
          if (data.done) {
            const duration = ((Date.now() - startTime) / 1000).toFixed(1);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === botMsgId
                  ? {
                    ...msg,
                    text: `${data.answer}\n\n*⏱️ Yanıt süresi: ${duration} saniye*`,
                    spokenText: data.answer,
                    isStreaming: false,
                    step: undefined
                  }
                  : msg
              )
            );
            setIsLoading(false);
            es.close();
            activeEventSourceRef.current = null;
          } else if (data.step) {
            setCurrentStep(data.step);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === botMsgId
                  ? { ...msg, step: data.step }
                  : msg
              )
            );
          }
        } catch (e) { }
      });
      es.addEventListener('error', () => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMsgId
              ? { ...msg, text: '❌ *Sizi anlayamadım veya bağlantı koptu.*', isStreaming: false, step: undefined }
              : msg
          )
        );
        setIsLoading(false);
        es.close();
        activeEventSourceRef.current = null;
      });
    } catch (error) {
      setMessages((prev) => [...prev, { id: `error-${Date.now()}`, text: 'Sizi anlayamadım.', sender: 'bot', timestamp: new Date() }]);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    flatListRef.current?.scrollToEnd({ animated: true });
  }, [messages, isLoading, currentStep]);

  const renderItem = ({ item }: { item: Message }) => {
    const isUser = item.sender === 'user';
    if (isUser) {
      return (
        <View style={styles.userMessageContainer}>
          <View style={styles.userBubble}>
            <Text style={styles.userText}>{item.text}</Text>
          </View>
        </View>
      );
    }
    return (
      <View style={styles.botMessageContainer}>
        <View style={styles.botAvatar}>
          <MaterialCommunityIcons name="cow" size={26} color="#2E7D32" />
        </View>
        <View style={styles.botContent}>
          <View style={styles.botHeaderRow}>
            <Text style={styles.botSenderName}>Çiftlik Asistanı</Text>
            {!item.isStreaming && item.text ? (
              <TouchableOpacity style={styles.speakerButton} onPress={() => speakText(item.id, item.spokenText ?? item.text)}>
                <Ionicons name={speakingId === item.id ? 'volume-high' : 'volume-medium-outline'} size={18} color={speakingId === item.id ? COLORS.primary : COLORS.textSecondary} />
              </TouchableOpacity>
            ) : null}
          </View>

          {/* SSE AKIŞI SIRASINDA CANLI STEP GÖSTERİMİ */}
          <Markdown style={markdownStyles} rules={markdownRules}>
            {item.text}
          </Markdown>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#fff" />

      {/* YENİ: SOHBET ÜST BARI VE BİLDİRİM ZİLİ */}
      <View style={styles.topBar}>
        <View style={styles.topBarTitleRow}>
          <MaterialCommunityIcons name="magic-staff" size={22} color="#1B5E20" />
          <Text style={styles.topBarTitle}>Çiftlik Asistanı</Text>
        </View>

        {/* ZİL BUTONU */}
        <TouchableOpacity style={styles.bellButton} onPress={() => setIsBellOpen(!isBellOpen)} activeOpacity={0.8}>
          <Ionicons name={unreadAlarms.length > 0 ? "notifications" : "notifications-outline"} size={26} color={unreadAlarms.length > 0 ? "#D32F2F" : "#546E7A"} />
          {unreadAlarms.length > 0 && (
            <View style={styles.bellBadge}>
              <Text style={styles.bellBadgeText}>{unreadAlarms.length}</Text>
            </View>
          )}
        </TouchableOpacity>
      </View>

      {/* YENİ: AÇILIR ZİL MENÜSÜ (DROPDOWN) */}
      {isBellOpen && (
        <View style={styles.dropdownContainer}>
          <View style={styles.dropdownHeader}>
            <Text style={styles.dropdownTitle}>🚨 Anlık Anomali Tespitleri</Text>
            <TouchableOpacity onPress={() => setIsBellOpen(false)}><Ionicons name="close" size={20} color="#78909C" /></TouchableOpacity>
          </View>

          {unreadAlarms.length > 0 ? (
            <ScrollView style={{ maxHeight: 250 }}>
              {unreadAlarms.map((alarm) => (
                <TouchableOpacity key={alarm.id} style={styles.dropdownItem} onPress={() => handleAlarmClick(alarm)}>
                  <View style={styles.dropdownItemHeader}>
                    <Text style={styles.dropdownCowName}>🐄 {alarm.isim} (TR{alarm.kupe_no})</Text>
                    <View style={styles.dropdownDropBadge}><Text style={styles.dropdownDropText}>-%{alarm.dusus_yuzdesi.toFixed(0)}</Text></View>
                  </View>
                  <Text style={styles.dropdownMsg} numberOfLines={2}>{alarm.mesaj}</Text>
                  <Text style={styles.dropdownActionHint}>Özetlerde İncele &rarr;</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          ) : (
            <View style={styles.dropdownEmpty}>
              <Ionicons name="checkmark-circle" size={32} color="#2E7D32" />
              <Text style={styles.dropdownEmptyText}>Şu an riskli veya sütü düşen inek bulunmuyor.</Text>
            </View>
          )}
        </View>
      )}

      {/* CHAT ALANI */}
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        ListEmptyComponent={
          <View style={styles.emptyChatContainer}>
            <View style={styles.emptyIconContainer}>
              <MaterialCommunityIcons name="barn" size={56} color="#388E3C" />
            </View>
            <Text style={styles.welcomeTitle}>Merhaba! Çiftliğinizle ilgili ne öğrenmek istersiniz?</Text>
            <Text style={styles.welcomeSubtitle}>Bugün çiftliğin verimi veya ineklerin sağlığı hakkında ne öğrenmek istersin?</Text>
          </View>
        }
        ListFooterComponent={
          isLoading ? (
            <View style={styles.loadingContainer}>
              <MaterialCommunityIcons name="cow" size={20} color="#388E3C" style={styles.loadingIcon} />
              <StepIndicator label={currentStep} />
            </View>
          ) : null
        }
      />

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}>
        <View style={styles.shortcutsWrapper}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.shortcutsContent}>
            {SHORTCUTS.map((shortcut, idx) => (
              <TouchableOpacity key={idx} style={styles.shortcutChip} onPress={() => !isLoading && sendMessage(shortcut.query)} disabled={isLoading}>
                <Text style={[styles.shortcutText, isLoading && { color: '#B0BEC5' }]}>{shortcut.label}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        <View style={styles.inputWrapper}>
          <View style={styles.inputContainer}>
            <TextInput
  style={styles.input}
  value={inputText}
  onChangeText={setInputText}
  placeholder={
    isLoading
      ? 'Çiftlik Asistanı yanıt hazırlıyor...'
      : 'Çiftlik Asistanına sorun...'
  }
  placeholderTextColor="#7cb342"
  maxLength={1000}
  editable={!isLoading && !isRecording}
  returnKeyType="send"
  enterKeyHint="send"
  blurOnSubmit={false}
  onSubmitEditing={() => {
    if (!isLoading && inputText.trim().length > 0) {
      sendMessage();
    }
  }}
/>

            {isLoading ? (
              /* İŞLEMİ GERİ ALMA / DURDURMA BUTONU */
              <TouchableOpacity style={styles.cancelButton} onPress={handleCancelStreaming}>
                <Ionicons name="stop" size={20} color="#fff" />
              </TouchableOpacity>
            ) : inputText.trim().length > 0 ? (
              <TouchableOpacity style={styles.sendButton} onPress={() => sendMessage()}>
                <Ionicons name="arrow-up" size={24} color="#fff" />
              </TouchableOpacity>
            ) : (
              <TouchableOpacity style={[styles.micButton, isRecording && styles.recordingActive]} onPress={isRecording ? stopRecording : startRecording}>
                <Ionicons name={isRecording ? "stop" : "mic"} size={24} color={isRecording ? "#fff" : "#2E7D32"} />
              </TouchableOpacity>
            )}
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const COLORS = {
  primary: '#1B5E20',
  primarySoft: '#2E7D32',
  background: '#F9FBF9',
  surface: '#FFFFFF',
  accent: '#4CAF50',
  textTitle: '#1B5E20',
  textPrimary: '#263238',
  textSecondary: '#546E7A',
  textMuted: '#8FA3AD',
  textBody: '#263238',
  textDark: '#1B5E20',
  secondary: '#F1F8E9',
  userBubble: '#E0F2F1',
  botBubble: '#FFFFFF',
  inputBg: '#F1F8F4',
  success: '#2E7D32',
  danger: '#D32F2F',
  border: '#E0E0E0',
};

const markdownStyles = StyleSheet.create({
  body: { color: COLORS.textBody, fontSize: 16, lineHeight: 24 },
  strong: { fontWeight: '700', color: COLORS.textDark },
  paragraph: { marginTop: 0, marginBottom: 12, flexWrap: 'wrap' },
  tableScrollView: { marginVertical: 12 },
  tableContent: { paddingRight: 10 },
  tableCard: { borderWidth: 1, borderColor: COLORS.border, borderRadius: 12, backgroundColor: '#fff', overflow: 'hidden', minWidth: 500 },
  tr: { flexDirection: 'row', borderBottomWidth: 1, borderColor: '#F1F8E9' },
  th: { padding: 12, backgroundColor: COLORS.secondary, borderRightWidth: 1, borderColor: '#C5E1A5', width: 120, justifyContent: 'center' },
  td: { padding: 12, borderRightWidth: 1, borderColor: '#F1F8E9', width: 120, justifyContent: 'center' },
  thText: { fontWeight: '700', fontSize: 14, color: COLORS.textDark },
  tdText: { fontSize: 14, color: '#333' }
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  listContent: { paddingHorizontal: 16, paddingBottom: 20, flexGrow: 1 },
  userMessageContainer: { alignSelf: 'flex-end', marginVertical: 12, maxWidth: '85%' },
  userBubble: { backgroundColor: COLORS.userBubble, borderRadius: 20, borderTopRightRadius: 4, paddingHorizontal: 18, paddingVertical: 14 },
  userText: { color: '#263238', fontSize: 16, lineHeight: 22 },
  botMessageContainer: { flexDirection: 'row', marginVertical: 12, width: '100%' },
  botAvatar: { marginRight: 12, width: 30, alignItems: 'center' },
  botContent: { flex: 1 },
  botSenderName: { fontSize: 14, fontWeight: 'bold', color: COLORS.primary, marginBottom: 4 },
  botHeaderRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  speakerButton: { padding: 4, marginBottom: 4 },

  // STREAMING ADIM BALONCUĞU STİLLERİ
  streamingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.secondary,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: 12,
    marginTop: 4,
    borderLeftWidth: 3,
    borderLeftColor: COLORS.primarySoft
  },
  streamingStepText: {
    color: COLORS.primarySoft,
    fontSize: 14,
    fontStyle: 'italic',
    fontWeight: '500'
  },

  loadingContainer: { flexDirection: 'row', alignItems: 'center', marginLeft: 42, marginTop: 5, marginBottom: 20 },
  loadingIcon: { marginRight: 8, opacity: 0.8 },
  inputWrapper: { backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: '#F1F8E9', paddingHorizontal: 16, paddingVertical: 12, paddingBottom: Platform.OS === 'ios' ? 8 : 12 },
  inputContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.inputBg, borderRadius: 28, paddingHorizontal: 8, paddingVertical: 6, minHeight: 52 },
  input: { flex: 1, fontSize: 16, color: '#33691E', marginHorizontal: 8, maxHeight: 120, minHeight: 40 },
  micButton: { width: 42, height: 42, justifyContent: 'center', alignItems: 'center', borderRadius: 21, backgroundColor: COLORS.secondary },
  recordingActive: { backgroundColor: COLORS.danger, elevation: 4 },
  sendButton: { width: 42, height: 42, backgroundColor: COLORS.primary, borderRadius: 21, justifyContent: 'center', alignItems: 'center' },

  // İPTAL ET / DURDUR BUTONU
  cancelButton: { width: 42, height: 42, backgroundColor: COLORS.danger, borderRadius: 21, justifyContent: 'center', alignItems: 'center' },

  emptyChatContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 60 },
  emptyIconContainer: { marginBottom: 24, padding: 24, backgroundColor: COLORS.secondary, borderRadius: 60, borderWidth: 1, borderColor: '#C5E1A5' },
  welcomeTitle: { fontSize: 24, fontWeight: 'bold', color: COLORS.primary, marginBottom: 12 },
  welcomeSubtitle: { fontSize: 16, color: '#558b2f', textAlign: 'center', paddingHorizontal: 40, lineHeight: 24 },
  shortcutsWrapper: { backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: '#F1F8E9', paddingVertical: 10 },
  shortcutsContent: { paddingHorizontal: 16, flexDirection: 'row' },
  shortcutChip: { backgroundColor: COLORS.secondary, borderRadius: 20, paddingHorizontal: 14, paddingVertical: 8, borderWidth: 1, borderColor: '#C5E1A5', marginRight: 8 },
  shortcutText: { color: COLORS.primarySoft, fontSize: 14, fontWeight: '600' },

  topBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F1F8E9', backgroundColor: '#F9FBF9', zIndex: 10 },
  topBarTitleRow: { flexDirection: 'row', alignItems: 'center' },
  topBarTitle: { fontSize: 16, fontWeight: 'bold', color: '#1B5E20', marginLeft: 8 },
  bellButton: { padding: 4, position: 'relative' },
  bellBadge: { position: 'absolute', top: 2, right: 2, backgroundColor: '#D32F2F', borderRadius: 10, minWidth: 18, height: 18, justifyContent: 'center', alignItems: 'center', borderWidth: 1.5, borderColor: '#fff' },
  bellBadgeText: { color: '#fff', fontSize: 10, fontWeight: 'bold' },

  // AÇILIR ZİL MENÜSÜ STİLLERİ
  dropdownContainer: { position: 'absolute', top: 56, right: 16, left: 16, backgroundColor: '#ffffff', borderRadius: 16, borderWidth: 1, borderColor: '#E0E8E0', padding: 12, zIndex: 100, elevation: 10, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 10 },
  dropdownHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 8, borderBottomWidth: 1, borderBottomColor: '#F1F8E9', marginBottom: 8 },
  dropdownTitle: { fontSize: 14, fontWeight: 'bold', color: '#D32F2F' },
  dropdownItem: { backgroundColor: '#FFEBEE', padding: 10, borderRadius: 10, marginBottom: 8, borderWidth: 1, borderColor: '#FFCDD2' },
  dropdownItemHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  dropdownCowName: { fontSize: 13, fontWeight: 'bold', color: '#B71C1C' },
  dropdownDropBadge: { backgroundColor: '#D32F2F', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  dropdownDropText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },
  dropdownMsg: { fontSize: 12, color: '#37474F', lineHeight: 16 },
  dropdownActionHint: { fontSize: 11, fontWeight: 'bold', color: '#1E88E5', marginTop: 6, textAlign: 'right' },
  dropdownEmpty: { padding: 20, alignItems: 'center', justifyContent: 'center' },
  dropdownEmptyText: { fontSize: 13, color: '#546E7A', marginTop: 8, textAlign: 'center' },
});