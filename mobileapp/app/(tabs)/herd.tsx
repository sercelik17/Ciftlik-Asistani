import React, { useEffect, useState } from 'react';
import {
  StyleSheet, Text, View, FlatList, TextInput, TouchableOpacity,
  ActivityIndicator, Modal, ScrollView, RefreshControl, Dimensions
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Constants from 'expo-constants';
import { useAuth } from '../../context/AuthContext';

interface Cow { kupe_no: string; isim: string; ortalama_sut: number; son_sut: number; durum: 'Sağlıklı' | 'Riskli'; }
interface CowStats { dates: string[]; yields: number[]; }

const getApiUrl = () => {
  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) return `http://${hostUri.split(':')[0]}:8001`;
  return `http://localhost:8001`;
};

const API_URL = getApiUrl();

export default function Herd() {
  const router = useRouter();
  const { token } = useAuth();
  const [cows, setCows] = useState<Cow[]>([]);
  const [filteredCows, setFilteredCows] = useState<Cow[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedCow, setSelectedCow] = useState<Cow | null>(null);
  const [cowStats, setCowStats] = useState<CowStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  const fetchCows = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/cows`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.cows) {
          setCows(data.cows);
          filterCows(data.cows, searchQuery);
        }
      }
    } catch (error) { console.error(error); } 
    finally { setLoading(false); setRefreshing(false); }
  };

  const fetchCowStats = async (kupeNo: string) => {
    if (!token) return;
    setStatsLoading(true);
    try {
      const res = await fetch(`${API_URL}/cows/${kupeNo}/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) setCowStats({ dates: data.dates || [], yields: data.yields || [] });
      }
    } catch (error) { console.error(error); } 
    finally { setStatsLoading(false); }
  };

  useEffect(() => {
    if (token) {
      fetchCows();
    }
  }, [token]);

  const filterCows = (allCows: Cow[], query: string) => {
    if (!query) { setFilteredCows(allCows); return; }
    const lowerQuery = query.toLowerCase();
    setFilteredCows(allCows.filter(c => c.isim.toLowerCase().includes(lowerQuery) || c.kupe_no.toLowerCase().includes(lowerQuery)));
  };

  const handleSearch = (text: string) => { setSearchQuery(text); filterCows(cows, text); };
  const handleCowPress = (cow: Cow) => { setSelectedCow(cow); fetchCowStats(cow.kupe_no); };

  // AHTAPOTA DOĞRUDAN DEEP LINKING
  const askAboutCow = (cow: Cow) => {
    setSelectedCow(null);
    setCowStats(null);
    router.push({
      pathname: '/chat',
      params: { query: `Küpe numarası ${cow.kupe_no} olan ${cow.isim} adlı ineğin verim durumu, süt değişimleri ve sağlığı nasıldır?` }
    });
  };

  if (loading && !refreshing) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#1B5E20" />
        <Text style={styles.loadingText}>Sürü bilgileri yükleniyor...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.searchContainer}>
        <View style={styles.searchBox}>
          <Ionicons name="search" size={20} color="#78909C" style={{ marginRight: 8 }} />
          <TextInput style={styles.searchInput} placeholder="İsim veya Küpe No ile ara..." value={searchQuery} onChangeText={handleSearch} placeholderTextColor="#90A4AE" />
          {searchQuery.length > 0 && <TouchableOpacity onPress={() => handleSearch('')}><Ionicons name="close-circle" size={20} color="#78909C" /></TouchableOpacity>}
        </View>
      </View>

      <FlatList
        data={filteredCows}
        keyExtractor={(item) => item.kupe_no}
        contentContainerStyle={styles.listContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchCows(); }} colors={['#1B5E20']} />}
        renderItem={({ item }) => {
          const isHealthy = item.durum === 'Sağlıklı';
          return (
            <TouchableOpacity style={styles.cowCard} activeOpacity={0.8} onPress={() => handleCowPress(item)}>
              <View style={styles.cardHeader}>
                <View style={styles.cowTitleRow}>
                  <MaterialCommunityIcons name="cow" size={24} color={isHealthy ? "#2E7D32" : "#D32F2F"} style={{ marginRight: 8 }} />
                  <View><Text style={styles.cowName}>{item.isim}</Text><Text style={styles.cowTag}>TR{item.kupe_no}</Text></View>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: isHealthy ? '#E8F5E9' : '#FFEBEE' }]}>
                  <Text style={[styles.statusText, { color: isHealthy ? '#2E7D32' : '#C62828' }]}>{item.durum}</Text>
                </View>
              </View>
              <View style={styles.cardStatsRow}>
                <View style={styles.cardStatBox}><Text style={styles.cardStatLabel}>Genel Ortalama</Text><Text style={styles.cardStatValue}>{item.ortalama_sut.toFixed(1)} L</Text></View>
                <View style={styles.cardStatBox}><Text style={styles.cardStatLabel}>Son Sağım</Text><Text style={styles.cardStatValue}>{item.son_sut.toFixed(1)} L</Text></View>
              </View>
            </TouchableOpacity>
          );
        }}
        ListEmptyComponent={<View style={styles.emptyContainer}><Ionicons name="alert-circle-outline" size={48} color="#B0BEC5" style={{ marginBottom: 12 }} /><Text style={styles.emptyText}>İnek bulunamadı.</Text></View>}
      />

      {/* MODAL */}
      <Modal visible={selectedCow !== null} animationType="slide" transparent={true} onRequestClose={() => setSelectedCow(null)}>
        <View style={styles.modalOverlay}>
          <TouchableOpacity style={styles.modalDismiss} activeOpacity={1} onPress={() => setSelectedCow(null)} />
          <View style={styles.modalContent}>
            {selectedCow && (
              <>
                <View style={styles.modalHeader}>
                  <View style={styles.modalHeaderTitle}>
                    <MaterialCommunityIcons name="cow" size={28} color={selectedCow.durum === 'Sağlıklı' ? "#2E7D32" : "#D32F2F"} style={{ marginRight: 8 }} />
                    <View><Text style={styles.modalCowName}>{selectedCow.isim}</Text><Text style={styles.modalCowTag}>TR{selectedCow.kupe_no}</Text></View>
                  </View>
                  <TouchableOpacity onPress={() => setSelectedCow(null)} style={styles.closeButton}><Ionicons name="close" size={24} color="#546E7A" /></TouchableOpacity>
                </View>

                <ScrollView contentContainerStyle={styles.modalScroll}>
                  <View style={styles.modalStatsGrid}>
                    <View style={styles.modalStatCard}><Text style={styles.modalStatLabel}>Sürü Durumu</Text><Text style={[styles.modalStatValue, { color: selectedCow.durum === 'Sağlıklı' ? '#2E7D32' : '#C62828', fontSize: 16 }]}>{selectedCow.durum}</Text></View>
                    <View style={styles.modalStatCard}><Text style={styles.modalStatLabel}>Ort. Süt</Text><Text style={styles.modalStatValue}>{selectedCow.ortalama_sut.toFixed(1)} L</Text></View>
                    <View style={styles.modalStatCard}><Text style={styles.modalStatLabel}>Son Verim</Text><Text style={styles.modalStatValue}>{selectedCow.son_sut.toFixed(1)} L</Text></View>
                  </View>

                  <Text style={styles.graphTitle}>📈 Son 10 Sağım Verimi (Litre)</Text>
                  {statsLoading ? (
                    <View style={styles.graphLoading}><ActivityIndicator size="small" color="#1B5E20" /></View>
                  ) : cowStats && cowStats.yields.length > 0 ? (
                    <View style={styles.chartContainer}>
                      <View style={styles.chartBarsContainer}>
                        {cowStats.yields.map((val, idx) => {
                          const maxVal = Math.max(...cowStats.yields, 1);
                          return (
                            <View key={idx} style={styles.chartCol}>
                              <View style={styles.barWrapper}><Text style={styles.barValueText}>{val.toFixed(1)}</Text><View style={[styles.chartBar, { height: `${(val / maxVal) * 80}%` }]} /></View>
                              <Text style={styles.chartLabelText} numberOfLines={1}>{cowStats.dates[idx].substring(5)}</Text>
                            </View>
                          );
                        })}
                      </View>
                    </View>
                  ) : <View style={styles.emptyChart}><Text style={styles.emptyChartText}>Geçmiş sağım kaydı bulunamadı.</Text></View>}

                  <TouchableOpacity style={styles.askButton} onPress={() => askAboutCow(selectedCow)}>
                    <Ionicons name="chatbubble-ellipses" size={20} color="#fff" style={{ marginRight: 8 }} />
                    <Text style={styles.askButtonText}>Çiftlik Asistanına Bu İnek Hakkında Sor</Text>
                  </TouchableOpacity>
                </ScrollView>
              </>
            )}
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FBF9' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 16, color: '#546E7A', fontWeight: '500' },
  searchContainer: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 8, backgroundColor: '#ffffff', borderBottomWidth: 1, borderBottomColor: '#f0f0f0' },
  searchBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F1F8F4', borderRadius: 12, paddingHorizontal: 12, height: 44, borderWidth: 1, borderColor: '#E0E8E0' },
  searchInput: { flex: 1, fontSize: 15, color: '#1B5E20' },
  listContent: { padding: 16, paddingBottom: 100 },
  cowCard: { backgroundColor: '#ffffff', borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: '#e8f0e8', elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  cowTitleRow: { flexDirection: 'row', alignItems: 'center' },
  cowName: { fontSize: 16, fontWeight: 'bold', color: '#263238' },
  cowTag: { fontSize: 12, color: '#78909C', marginTop: 1 },
  statusBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  statusText: { fontSize: 11, fontWeight: 'bold' },
  cardStatsRow: { flexDirection: 'row', justifyContent: 'space-between', backgroundColor: '#F9FBF9', borderRadius: 10, padding: 10, borderWidth: 1, borderColor: '#f0f4f0' },
  cardStatBox: { flex: 1 },
  cardStatLabel: { fontSize: 10, color: '#78909C', marginBottom: 2 },
  cardStatValue: { fontSize: 15, fontWeight: 'bold', color: '#37474F' },
  emptyContainer: { alignItems: 'center', paddingVertical: 60 },
  emptyText: { fontSize: 14, color: '#78909C' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  modalDismiss: { flex: 1 },
  modalContent: { backgroundColor: '#ffffff', borderTopLeftRadius: 24, borderTopRightRadius: 24, maxHeight: '85%', minHeight: '60%', paddingBottom: 24 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 18, borderBottomWidth: 1, borderBottomColor: '#f0f0f0' },
  modalHeaderTitle: { flexDirection: 'row', alignItems: 'center' },
  modalCowName: { fontSize: 18, fontWeight: 'bold', color: '#263238' },
  modalCowTag: { fontSize: 13, color: '#78909C' },
  closeButton: { padding: 4 },
  modalScroll: { padding: 20, paddingBottom: 40 },
  modalStatsGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20 },
  modalStatCard: { flex: 1, backgroundColor: '#F5F7F6', borderWidth: 1, borderColor: '#e8ebe8', borderRadius: 12, padding: 10, alignItems: 'center', marginHorizontal: 3 },
  modalStatLabel: { fontSize: 10, color: '#78909C', marginBottom: 4 },
  modalStatValue: { fontSize: 15, fontWeight: 'bold', color: '#263238' },
  graphTitle: { fontSize: 14, fontWeight: 'bold', color: '#1B5E20', marginBottom: 12, marginTop: 6 },
  graphLoading: { height: 120, justifyContent: 'center', alignItems: 'center' },
  chartContainer: { height: 160, backgroundColor: '#F9FBF9', borderRadius: 16, padding: 12, borderWidth: 1, borderColor: '#e8f0e8', marginBottom: 20, justifyContent: 'flex-end' },
  chartBarsContainer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', height: '100%' },
  chartCol: { alignItems: 'center', flex: 1, marginHorizontal: 2 },
  barWrapper: { flex: 1, justifyContent: 'flex-end', alignItems: 'center', width: '100%' },
  chartBar: { width: 8, backgroundColor: '#2E7D32', borderTopLeftRadius: 4, borderTopRightRadius: 4 },
  barValueText: { fontSize: 9, fontWeight: 'bold', color: '#1B5E20', marginBottom: 2 },
  chartLabelText: { fontSize: 8, color: '#78909C', marginTop: 4 },
  emptyChart: { height: 120, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F5F5F5', borderRadius: 16, marginBottom: 20 },
  emptyChartText: { fontSize: 12, color: '#90A4AE' },
  askButton: { flexDirection: 'row', backgroundColor: '#1B5E20', borderRadius: 14, height: 48, alignItems: 'center', justifyContent: 'center', marginTop: 10, elevation: 2 },
  askButtonText: { color: '#ffffff', fontSize: 14, fontWeight: 'bold' }
});