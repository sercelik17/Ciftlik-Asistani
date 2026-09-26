import React, { useEffect, useState } from 'react';
import {
  StyleSheet, Text, View, ScrollView, TouchableOpacity,
  ActivityIndicator, FlatList, Alert, RefreshControl, Modal,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import Constants from 'expo-constants';
import { useAuth } from '../../context/AuthContext';

interface Alarm {
  id: number; kupe_no: string; isim: string; tarih: string;
  sagim_zamani: string; eski_ortalama: number; son_verim: number;
  dusus_yuzdesi: number; mesaj: string; okundu: boolean;
}

interface Summary {
  id: number; tarih: string; dunku_toplam_sut: number; bugunku_toplam_sut: number;
  en_verimli_inek_kupe_no: string | null; en_verimli_inek_isim: string | null; mesaj: string;
}

interface CowDailyChange {
  kupe_no: string; isim: string; dunku_sut: number; bugunku_sut: number; degisim_orani: number;
}

const getApiUrl = () => {
  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) return `http://${hostUri.split(':')[0]}:8001`;
  return `http://localhost:8001`;
};

const API_URL = getApiUrl();

export default function Dashboard() {
  const router = useRouter();
  const { token } = useAuth();
  const params = useLocalSearchParams();
  const highlightCow = params.highlight_cow;
  const alertMsg = params.alert_msg;

  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [cowsDailyData, setCowsDailyData] = useState<CowDailyChange[]>([]);
  const [tableLoading, setTableLoading] = useState(false);

  const fetchData = async () => {
    if (!token) return;
    try {
      const [alarmsRes, summariesRes] = await Promise.all([
        fetch(`${API_URL}/alarms?unread_only=true`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/summaries`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
      ]);
      if (alarmsRes.ok) setAlarms((await alarmsRes.json()).alarms || []);
      if (summariesRes.ok) setSummaries((await summariesRes.json()).summaries || []);
    } catch (error) { console.error(error); }
    finally { setLoading(false); setRefreshing(false); }
  };

  useEffect(() => {
    if (token) {
      fetchData();
      const interval = setInterval(fetchData, 30000);
      return () => clearInterval(interval);
    }
  }, [token]);

  useEffect(() => {
    if (alertMsg) {
      Alert.alert(
        `🐄 TR${highlightCow} Alarmı`,
        alertMsg as string,
        [
          {
            text: 'Tamam',
            onPress: () => {
              router.setParams({ highlight_cow: undefined, alert_msg: undefined });
            }
          }
        ]
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alertMsg, highlightCow]);

  const handleOpenSummaryModal = async () => {
    setModalVisible(true);
    setTableLoading(true);
    try {
      const res = await fetch(`${API_URL}/cows/daily-change`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok && data.success) setCowsDailyData(data.data || []);
    } catch (e) { Alert.alert('Hata', 'Tablo verileri alınamadı.'); }
    finally { setTableLoading(false); }
  };

  const markAlarmAsRead = async (alarmId: number) => {
    try {
      setAlarms((prev) => prev.filter((a) => a.id !== alarmId));
      await fetch(`${API_URL}/alarms/${alarmId}/read`, { 
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
    } catch (error) { fetchData(); }
  };

  const runSimulation = async (type: 'sabah' | 'aksam' | 'check' | 'summary') => {
    setActionLoading(type);
    let endpoint = type === 'sabah' ? '/simule-data/sabah' :
      type === 'aksam' ? '/simule-data/aksam' :
        type === 'check' ? '/alarms/check' : '/alarms/daily-summary';
    try {
      const res = await fetch(`${API_URL}${endpoint}`, { 
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok && data.success) {
        Alert.alert('Başarılı', data.message || 'İşlem tamamlandı.');
        fetchData();
      } else Alert.alert('Hata', data.detail || 'İşlem gerçekleştirilemedi.');
    } catch (error) { Alert.alert('Bağlantı Hatası', 'Backend sunucusuna bağlanılamadı.'); }
    finally { setActionLoading(null); }
  };

  const latestSummary = summaries[0];

  if (loading && !refreshing) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#1B5E20" />
        <Text style={styles.loadingText}>Denetim masası yükleniyor...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView style={styles.container} contentContainerStyle={styles.content} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchData(); }} colors={['#1B5E20']} />}>

        {/* AHTAPOT YÖNLENDİRME KARTI */}
        <TouchableOpacity style={styles.agentBanner} onPress={() => router.push('/chat')} activeOpacity={0.9}>
          <MaterialCommunityIcons name="magic-staff" size={28} color="#fff" />
          <View style={{ flex: 1, marginLeft: 12 }}>
            <Text style={styles.agentBannerTitle}>Çiftlik Asistanı Yanınızda</Text>
            <Text style={styles.agentBannerSub}>Veri analizi yapmak, grafikleri çizdirmek veya alarmları sormak için tıklayın.</Text>
          </View>
          <Ionicons name="chevron-forward" size={22} color="#fff" />
        </TouchableOpacity>

        {/* 1. ÖZET KARTI */}
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>📊 Çiftlik Durum Özeti</Text>
          <Text style={styles.hintText}>(Detaylı tablo için tıkla)</Text>
        </View>

        {latestSummary ? (
          <TouchableOpacity style={styles.summaryCard} activeOpacity={0.8} onPress={handleOpenSummaryModal}>
            <View style={styles.summaryHeader}>
              <View style={styles.dateBadge}>
                <Ionicons name="calendar-outline" size={16} color="#1B5E20" style={{ marginRight: 6 }} />
                <Text style={styles.dateText}>{latestSummary.tarih}</Text>
              </View>
              <View style={styles.summaryBadge}><Text style={styles.summaryBadgeText}>Son Rapor</Text></View>
            </View>

            <View style={styles.statsGrid}>
              <View style={styles.statBox}>
                <Text style={styles.statLabel}>Bugün Üretilen</Text>
                <Text style={styles.statValue}>{latestSummary.bugunku_toplam_sut.toFixed(1)} L</Text>
              </View>
              <View style={styles.statBox}>
                <Text style={styles.statLabel}>Dün Üretilen</Text>
                <Text style={styles.statValue}>{latestSummary.dunku_toplam_sut.toFixed(1)} L</Text>
              </View>
            </View>

            {(() => {
              const diff = latestSummary.bugunku_toplam_sut - latestSummary.dunku_toplam_sut;
              const isIncrease = diff >= 0;
              return (
                <View style={[styles.trendRow, { backgroundColor: isIncrease ? '#E8F5E9' : '#FFEBEE' }]}>
                  <Ionicons name={isIncrease ? 'trending-up' : 'trending-down'} size={18} color={isIncrease ? '#2E7D32' : '#C62828'} style={{ marginRight: 6 }} />
                  <Text style={[styles.trendText, { color: isIncrease ? '#2E7D32' : '#C62828' }]}>
                    Düne göre {isIncrease ? 'artış' : 'düşüş'}: {Math.abs(diff).toFixed(1)} Litre
                  </Text>
                </View>
              );
            })()}

            {latestSummary.en_verimli_inek_isim && (
              <View style={styles.championRow}>
                <View style={styles.championIconCircle}><Ionicons name="trophy" size={20} color="#F9A825" /></View>
                <View style={styles.championInfo}>
                  <Text style={styles.championLabel}>Günün Şampiyonu</Text>
                  <Text style={styles.championName}>{latestSummary.en_verimli_inek_isim} <Text style={styles.tagText}>({latestSummary.en_verimli_inek_kupe_no})</Text></Text>
                </View>
              </View>
            )}
          </TouchableOpacity>
        ) : (
          <View style={styles.emptyCard}><Text style={styles.emptyCardText}>Henüz günlük özet oluşturulmamış.</Text></View>
        )}

        {/* 2. ACİL ALARMLAR */}
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>🚨 Acil Durum Alarmları</Text>
          {alarms.length > 0 && <View style={styles.alarmBadge}><Text style={styles.alarmBadgeText}>{alarms.length} Yeni</Text></View>}
        </View>

        {alarms.length > 0 ? (
          <FlatList
            data={alarms}
            scrollEnabled={false}
            keyExtractor={(item) => item.id.toString()}
            renderItem={({ item }) => (
              <TouchableOpacity style={styles.alarmCard} activeOpacity={0.8} onPress={() => markAlarmAsRead(item.id)}>
                <View style={styles.alarmHeader}>
                  <View style={styles.cowInfo}>
                    <MaterialCommunityIcons name="cow" size={18} color="#D32F2F" style={{ marginRight: 6 }} />
                    <Text style={styles.cowName}>{item.isim}</Text><Text style={styles.cowTag}>({item.kupe_no})</Text>
                  </View>
                  <View style={styles.readButton}><Text style={styles.readButtonText}>Kapat</Text></View>
                </View>
                <View style={styles.alarmSubRow}>
                  <View style={styles.dropBadge}><Text style={styles.dropText}>Düşüş: %{item.dusus_yuzdesi.toFixed(0)}</Text></View>
                  <Text style={styles.alarmTime}>{item.tarih} - {item.sagim_zamani === 'm' ? 'Sabah' : 'Akşam'}</Text>
                </View>
                <Text style={styles.alarmMessage}>{item.mesaj}</Text>
              </TouchableOpacity>
            )}
          />
        ) : (
          <View style={styles.noAlarmsCard}>
            <Ionicons name="checkmark-circle" size={32} color="#2E7D32" style={{ marginBottom: 6 }} />
            <Text style={styles.noAlarmsText}>Her Şey Yolunda!</Text>
          </View>
        )}

        {/* 3. SİMÜLASYON BUTONLARI */}

      </ScrollView>

      {/* MODAL */}
      <Modal animationType="slide" transparent={true} visible={modalVisible} onRequestClose={() => setModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContainer}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>🐄 Günlük Verim Tablosu</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.closeButton}><Ionicons name="close" size={24} color="#37474F" /></TouchableOpacity>
            </View>
            {tableLoading ? (
              <View style={{ padding: 40, alignItems: 'center' }}><ActivityIndicator size="large" color="#1B5E20" /><Text style={styles.loadingText}>Hesaplanıyor...</Text></View>
            ) : (
              <FlatList
                data={cowsDailyData}
                keyExtractor={(item) => item.kupe_no}
                renderItem={({ item }) => {
                  const isPositive = item.degisim_orani >= 0;
                  return (
                    <View style={styles.tableRow}>
                      <View style={{ flex: 2.5 }}><Text style={styles.rowName}>{item.isim}</Text><Text style={styles.rowTag}>{item.kupe_no}</Text></View>
                      <Text style={[styles.rowCell, { flex: 1.2 }]}>{item.dunku_sut} L</Text>
                      <Text style={[styles.rowCell, { flex: 1.2, fontWeight: 'bold' }]}>{item.bugunku_sut} L</Text>
                      <View style={{ flex: 1.5, alignItems: 'flex-end' }}>
                        <View style={[styles.rateBadge, { backgroundColor: isPositive ? '#E8F5E9' : '#FFEBEE' }]}>
                          <Text style={[styles.rateText, { color: isPositive ? '#2E7D32' : '#C62828' }]}>{isPositive ? `+${item.degisim_orani}%` : `${item.degisim_orani}%`}</Text>
                        </View>
                      </View>
                    </View>
                  );
                }}
              />
            )}
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FBF9' },
  content: { padding: 16, paddingBottom: 100 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 16, color: '#546E7A', fontWeight: '500' },
  agentBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1E88E5', padding: 16, borderRadius: 16, marginBottom: 16, elevation: 4 },
  agentBannerTitle: { fontSize: 16, fontWeight: 'bold', color: '#fff' },
  agentBannerSub: { fontSize: 12, color: 'rgba(255,255,255,0.9)', marginTop: 2 },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#1B5E20' },
  hintText: { fontSize: 12, color: '#78909C', marginLeft: 6 },
  sectionHeaderRow: { flexDirection: 'row', alignItems: 'baseline', marginTop: 14, marginBottom: 10 },
  summaryCard: { backgroundColor: '#ffffff', borderRadius: 16, padding: 16, borderWidth: 1, borderColor: '#e8f0e8', elevation: 3 },
  summaryHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  dateBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F1F8E9', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  dateText: { fontSize: 12, fontWeight: 'bold', color: '#1B5E20' },
  summaryBadge: { backgroundColor: '#E0F2F1', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  summaryBadgeText: { fontSize: 10, fontWeight: 'bold', color: '#004D40' },
  statsGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  statBox: { flex: 1, backgroundColor: '#F9FBF9', borderRadius: 12, padding: 12, marginRight: 8, borderWidth: 1, borderColor: '#f0f4f0' },
  statLabel: { fontSize: 11, color: '#546E7A', marginBottom: 4 },
  statValue: { fontSize: 20, fontWeight: 'bold', color: '#263238' },
  trendRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10, marginBottom: 12 },
  trendText: { fontSize: 13, fontWeight: '600' },
  championRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFFDE7', padding: 12, borderRadius: 12, borderWidth: 1, borderColor: '#FFF9C4' },
  championIconCircle: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#FFF9C4', justifyContent: 'center', alignItems: 'center', marginRight: 10 },
  championInfo: { flex: 1 },
  championLabel: { fontSize: 10, color: '#F57F17', fontWeight: 'bold', textTransform: 'uppercase' },
  championName: { fontSize: 14, fontWeight: 'bold', color: '#263238' },
  tagText: { fontWeight: 'normal', color: '#546E7A', fontSize: 12 },
  emptyCard: { backgroundColor: '#ffffff', borderRadius: 16, padding: 24, alignItems: 'center', borderWidth: 1, borderColor: '#e8e8e8' },
  emptyCardText: { fontSize: 15, fontWeight: 'bold', color: '#546E7A' },
  alarmBadge: { backgroundColor: '#FFEBEE', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10, marginLeft: 8 },
  alarmBadgeText: { fontSize: 11, fontWeight: 'bold', color: '#C62828' },
  alarmCard: { backgroundColor: '#ffffff', borderRadius: 14, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: '#FFEBEE', borderLeftWidth: 4, borderLeftColor: '#D32F2F' },
  alarmHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  cowInfo: { flexDirection: 'row', alignItems: 'center' },
  cowName: { fontSize: 14, fontWeight: 'bold', color: '#263238' },
  cowTag: { fontSize: 12, color: '#78909C', marginLeft: 4 },
  readButton: { backgroundColor: '#F5F5F5', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  readButtonText: { fontSize: 11, fontWeight: 'bold', color: '#78909C' },
  alarmSubRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  dropBadge: { backgroundColor: '#FFEBEE', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  dropText: { fontSize: 11, fontWeight: 'bold', color: '#C62828' },
  alarmTime: { fontSize: 11, color: '#90A4AE' },
  alarmMessage: { fontSize: 13, color: '#37474F', lineHeight: 18 },
  noAlarmsCard: { backgroundColor: '#E8F5E9', borderRadius: 14, padding: 20, alignItems: 'center', borderWidth: 1, borderColor: '#C8E6C9' },
  noAlarmsText: { fontSize: 15, fontWeight: 'bold', color: '#2E7D32' },
  simGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  simButton: { flex: 1, backgroundColor: '#1E88E5', borderRadius: 14, padding: 14, alignItems: 'center', justifyContent: 'center', marginHorizontal: 4, elevation: 2, minHeight: 80 },
  simButtonText: { fontSize: 13, fontWeight: 'bold', color: '#ffffff' },
  simButtonSub: { fontSize: 10, color: 'rgba(255,255,255,0.8)', marginTop: 2 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0, 0, 0, 0.5)', justifyContent: 'flex-end' },
  modalContainer: { backgroundColor: '#ffffff', borderTopLeftRadius: 24, borderTopRightRadius: 24, maxHeight: '80%', padding: 16 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: '#EEEEEE', marginBottom: 10 },
  modalTitle: { fontSize: 16, fontWeight: 'bold', color: '#1B5E20' },
  closeButton: { padding: 4 },
  tableHeader: { flexDirection: 'row', backgroundColor: '#F1F8E9', paddingVertical: 10, paddingHorizontal: 8, borderRadius: 8, marginBottom: 8 },
  columnHeader: { fontSize: 12, fontWeight: 'bold', color: '#2E7D32' },
  tableRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, paddingHorizontal: 8, borderBottomWidth: 1, borderBottomColor: '#F5F5F5' },
  rowName: { fontSize: 13, fontWeight: 'bold', color: '#263238' },
  rowTag: { fontSize: 11, color: '#78909C' },
  rowCell: { fontSize: 13, color: '#37474F' },
  rateBadge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  rateText: { fontSize: 12, fontWeight: 'bold' }
});