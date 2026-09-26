import React, { useEffect, useState } from 'react';
import {
  StyleSheet, Text, View, ScrollView, ActivityIndicator,
  TouchableOpacity, RefreshControl, Dimensions
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Constants from 'expo-constants';
import { useAuth } from '../../context/AuthContext';


interface Cow {
  kupe_no: string;
  isim: string;
  ortalama_sut: number;
  son_sut: number;
  durum: 'Sağlıklı' | 'Riskli';
}

interface SegmentedCows {
  elite: Cow[];
  standard: Cow[];
  weak: Cow[];
}

interface FarmTrend {
  dates: string[];
  yields: number[];
  currentAvg: number;
  previousAvg: number;
  diffPct: number;
  isPositive: boolean;
}

interface RiskyCow extends Cow {
  riskType: 'dalgalanma' | 'kronik';
  riskMessage: string;
}

const getApiUrl = () => {
  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) return `http://${hostUri.split(':')[0]}:8001`;
  return `http://localhost:8001`;
};

const API_URL = getApiUrl();
const screenWidth = Dimensions.get('window').width - 32;

export default function Statistics() {
  const router = useRouter();
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);

  const [activeTab, setActiveTab] = useState<'elite' | 'standard' | 'weak'>('elite');
  const [segmented, setSegmented] = useState<SegmentedCows>({ elite: [], standard: [], weak: [] });
  const [farmTrend, setFarmTrend] = useState<FarmTrend | null>(null);
  const [riskList, setRiskList] = useState<RiskyCow[]>([]);

  // 1. Çiftlik Grafik Verisi
  const fetchFarmStats = async () => {
    if (!token) return;
    setChartLoading(true);
    try {
      const res = await fetch(`${API_URL}/stats/farm`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.yields && data.yields.length >= 2) {
          const yields: number[] = data.yields;
          const dates: string[] = data.dates;
          const latest = yields[yields.length - 1];

          const prevAvg = yields.slice(0, yields.length - 1).reduce((a, b) => a + b, 0) / (yields.length - 1);
          const diffPct = ((latest - prevAvg) / (prevAvg || 1)) * 100;

          setFarmTrend({
            dates,
            yields,
            currentAvg: Number(latest.toFixed(1)),
            previousAvg: Number(prevAvg.toFixed(1)),
            diffPct: Number(diffPct.toFixed(1)),
            isPositive: diffPct >= 0,
          });
        }
      }
    } catch (error) {
      console.error("Grafik verisi alınamadı:", error);
    } finally {
      setChartLoading(false);
    }
  };

  // 2. İnek ve Risk Verileri
  const fetchAllAnalytics = async () => {
    if (!token) return;
    try {
      const [cowsRes, alarmsRes] = await Promise.all([
        fetch(`${API_URL}/cows`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/alarms`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
      ]);

      let allCows: Cow[] = [];
      if (cowsRes.ok) {
        const data = await cowsRes.json();
        if (data.success && data.cows) {
          allCows = data.cows;

          const sorted = [...allCows].sort((a, b) => b.ortalama_sut - a.ortalama_sut);
          const totalCount = sorted.length;
          const top20Count = Math.max(1, Math.ceil(totalCount * 0.20));
          const bottom20Count = Math.max(1, Math.ceil(totalCount * 0.20));

          const elite = sorted.slice(0, top20Count);
          const weak = sorted.slice(totalCount - bottom20Count);
          const standard = sorted.slice(top20Count, totalCount - bottom20Count);

          setSegmented({ elite, standard, weak });
        }
      }

      // Risk Hesaplama
      let alarmCounts: { [key: string]: number } = {};
      if (alarmsRes.ok) {
        const alarmData = await alarmsRes.json();
        if (alarmData.success && alarmData.alarms) {
          alarmData.alarms.forEach((a: any) => {
            alarmCounts[a.kupe_no] = (alarmCounts[a.kupe_no] || 0) + 1;
          });
        }
      }

      const calculatedRisks: RiskyCow[] = [];
      allCows.forEach((cow) => {
        const diffRatio = Math.abs(cow.son_sut - cow.ortalama_sut) / (cow.ortalama_sut || 1) * 100;
        const alarmCount = alarmCounts[cow.kupe_no] || 0;

        if (alarmCount >= 2 || cow.durum === 'Riskli') {
          calculatedRisks.push({
            ...cow,
            riskType: 'kronik',
            riskMessage: `🚨 ${alarmCount > 0 ? alarmCount + ' kez alarm' : 'Riskli'}`,
          });
        } else if (diffRatio >= 15 && cow.ortalama_sut > 5) {
          calculatedRisks.push({
            ...cow,
            riskType: 'dalgalanma',
            riskMessage: `⚡ %${diffRatio.toFixed(0)} dalgalanma`,
          });
        }
      });

      setRiskList(calculatedRisks);
    } catch (error) {
      console.error('Analiz verileri yüklenirken hata:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchFarmStats();
      fetchAllAnalytics();
    }
  }, [token]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchFarmStats();
    fetchAllAnalytics();
  };

  if (loading && !refreshing) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#1B5E20" />
        <Text style={styles.loadingText}>Çiftlik Analiz Panosu Hazırlanıyor...</Text>
      </View>
    );
  }

  const currentList = segmented[activeTab];
  const totalCowsCount = segmented.elite.length + segmented.standard.length + segmented.weak.length || 1;

  const gunlukOrtalama = farmTrend?.yields.length
    ? farmTrend.yields.reduce((a, b) => a + b, 0) / farmTrend.yields.length
    : 0;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} colors={['#1B5E20']} />}
    >
      {/* AI Asistan Banner */}
      <TouchableOpacity
        style={styles.aiBanner}
        onPress={() => router.push({
          pathname: '/chat',
          params: { query: `Çiftliğimin son 10 günlük süt üretim eğrisini ve trendini, ABC segmentasyonundaki ${segmented.elite.length} elit, ${segmented.weak.length} zayıf ineğimin durumunu ve alt risk panosundaki dalgalanmaları detaylı yorumla. Stratejik tavsiye ver.` }
        })}
        activeOpacity={0.9}
      >
        <View style={styles.aiIconCircle}>
          <MaterialCommunityIcons name="robot-outline" size={32} color="#ffffff" />
        </View>
        <View style={styles.aiTextContainer}>
          <Text style={styles.aiTitle}>Çiftlik Asistanına Yorumlat</Text>
          <Text style={styles.aiSub}>Sürü verimi, dalgalanmalar ve damızlık seçimi için anlık YZ analizi</Text>
        </View>
        <Ionicons name="chevron-forward" size={26} color="#ffffff" />
      </TouchableOpacity>

      {/* Sürü Süt Üretim Grafiği */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={{ flexShrink: 1, marginRight: 8 }}>
            <Text style={styles.cardTitle}>📊 Sürü Süt Üretim Grafiği</Text>
            <Text style={styles.cardSub}>Son 10 günün toplam sağım performansı (Litre)</Text>
          </View>
          <View style={styles.periodBadge}>
            <Text style={styles.periodBadgeText}>SON 10 GÜN</Text>
          </View>
        </View>

        {chartLoading ? (
          <View style={styles.chartLoader}>
            <ActivityIndicator size="large" color="#1B5E20" />
          </View>
        ) : farmTrend && farmTrend.yields.length > 0 ? (
          <>
            <View style={styles.chartContainer}>
              <View style={styles.chartBarsContainer}>
                {farmTrend.yields.map((val, idx) => {
                  const maxVal = Math.max(...farmTrend.yields, 1);
                  const isAboveAverage = val >= gunlukOrtalama;
                  const barColor = isAboveAverage ? '#2E7D32' : '#EF6C00';
                  const textColor = isAboveAverage ? '#1B5E20' : '#E65100';

                  // Tarihi GG/AA (DD/MM) formatına çeviriyoruz
                  const dateParts = farmTrend.dates[idx].split('-');
                  const formattedDate = dateParts.length === 3 ? `${dateParts[2]}/${dateParts[1]}` : farmTrend.dates[idx];

                  return (
                    <View key={idx} style={styles.chartCol}>
                      <View style={styles.barWrapper}>
                        <Text style={[styles.barValueText, { color: textColor }]} allowFontScaling={false}>
                          {Math.round(val)}
                        </Text>
                        <View style={[styles.chartBar, { height: `${(val / maxVal) * 80}%`, backgroundColor: barColor }]} />
                      </View>
                      <Text style={styles.chartLabelText} numberOfLines={1} allowFontScaling={false}>
                        {formattedDate}
                      </Text>
                    </View>
                  );
                })}
              </View>
            </View>

            <View style={styles.chartLegend}>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: '#2E7D32' }]} />
                <Text style={styles.legendText}>Ortalama ve üzeri gün</Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: '#EF6C00' }]} />
                <Text style={styles.legendText}>Ortalamanın altındaki gün</Text>
              </View>
            </View>

            <View style={styles.trendSummary}>
              <Text style={styles.trendBigValue}>{farmTrend.currentAvg} L</Text>
              <Text style={styles.trendLabel}>Bugünkü Toplam Sağım</Text>

              <View style={[styles.trendBadge, { backgroundColor: farmTrend.isPositive ? '#E8F5E9' : '#FFEBEE' }]}>
                <Ionicons
                  name={farmTrend.isPositive ? 'trending-up' : 'trending-down'}
                  size={20}
                  color={farmTrend.isPositive ? '#2E7D32' : '#C62828'}
                />
                <Text style={[styles.trendBadgeText, { color: farmTrend.isPositive ? '#2E7D32' : '#C62828' }]}>
                  {farmTrend.isPositive ? '↑' : '↓'} {Math.abs(farmTrend.currentAvg - farmTrend.previousAvg).toFixed(1)} L
                  ({farmTrend.isPositive ? '+' : ''}{farmTrend.diffPct}%)
                </Text>
              </View>
            </View>
          </>
        ) : (
          <View style={styles.chartLoader}><Text style={styles.emptyText}>Grafik verisi yükleniyor...</Text></View>
        )}
      </View>

      {/* ABC Sürü Dağılımı */}
      <View style={[styles.card, { marginTop: 20 }]}>
        <Text style={styles.cardTitle}>🏆 ABC Sürü Dağılımı</Text>
        <Text style={styles.cardSub}>Verimlilik segmentasyonu ve damızlık potansiyeli</Text>

        <View style={styles.visualBarContainer}>
          <View style={[styles.visualBarSegment, { flex: segmented.elite.length || 0.1, backgroundColor: '#FBC02D' }]} />
          <View style={[styles.visualBarSegment, { flex: segmented.standard.length || 0.1, backgroundColor: '#4CAF50' }]} />
          <View style={[styles.visualBarSegment, { flex: segmented.weak.length || 0.1, backgroundColor: '#E53935' }]} />
        </View>

        <View style={styles.visualBarLegend}>
          <Text style={styles.legendText}>🟡 Elit (%{Math.round((segmented.elite.length / totalCowsCount) * 100)})</Text>
          <Text style={styles.legendText}>🟢 Standart (%{Math.round((segmented.standard.length / totalCowsCount) * 100)})</Text>
          <Text style={styles.legendText}>🔴 Zayıf (%{Math.round((segmented.weak.length / totalCowsCount) * 100)})</Text>
        </View>

        {/* Sekmeler ve Liste (kısaltıldı - istersen tam hali için söyle) */}
        <View style={styles.segmentTabsRow}>
          {(['elite', 'standard', 'weak'] as const).map((tab) => (
            <TouchableOpacity
              key={tab}
              style={[styles.segmentTab, activeTab === tab && (styles as any)[`tabActive${tab.charAt(0).toUpperCase() + tab.slice(1)}`]]}
              onPress={() => setActiveTab(tab)}
            >
              <Text style={[styles.tabTitle, activeTab === tab && { color: tab === 'elite' ? '#F57F17' : tab === 'weak' ? '#C62828' : '#2E7D32' }]}>
                {tab === 'elite' ? '🌟 Elit' : tab === 'standard' ? '🟢 Standart' : '🔻 Zayıf'}
              </Text>
              <Text style={styles.tabCount}>{segmented[tab].length} İnek</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Liste */}
        <View style={styles.listContainer}>
          {currentList.map((cow, idx) => (
            <TouchableOpacity
              key={cow.kupe_no}
              style={styles.cowRow}
              onPress={() => router.push({ pathname: '/chat', params: { query: `TR${cow.kupe_no} küpe numaralı ${cow.isim} adlı ineğim için besleme ve damızlık önerisi ver.` } })}
            >
              <View style={styles.cowRowLeft}>
                <View style={[styles.rankBadge, { backgroundColor: activeTab === 'elite' ? '#FFF9C4' : activeTab === 'weak' ? '#FFCDD2' : '#E8F5E9' }]}>
                  <Text style={styles.rankText}>#{idx + 1}</Text>
                </View>
                <View style={{ marginLeft: 12 }}>
                  <Text style={styles.cowNameText}>{cow.isim}</Text>
                  <Text style={styles.cowTagText}>TR{cow.kupe_no}</Text>
                </View>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <Text style={styles.avgMilkText}>{cow.ortalama_sut.toFixed(1)} L</Text>
                <Text style={styles.avgLabelText}>Ortalama</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Kritik Dalgalanma Raporu */}
      <View style={[styles.card, { marginTop: 20, borderColor: '#FFCDD2' }]}>
        <View style={styles.cardHeader}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Ionicons name="flash" size={24} color="#D32F2F" />
            <Text style={[styles.cardTitle, { color: '#D32F2F', marginLeft: 8 }]}>Kritik Dalgalanma Raporu</Text>
          </View>
          {riskList.length > 0 && <View style={styles.riskBadge}><Text style={styles.riskBadgeText}>{riskList.length}</Text></View>}
        </View>

        {riskList.length > 0 ? (
          riskList.map((cow) => (
            <TouchableOpacity key={cow.kupe_no} style={styles.riskItem} onPress={() => router.push({ pathname: '/chat', params: { query: `TR${cow.kupe_no} ${cow.isim} ineği dalgalanma raporu` } })}>
              <Text style={styles.riskCowName}>🐄 {cow.isim} <Text style={styles.riskTag}>(TR{cow.kupe_no})</Text></Text>
              <Text style={styles.riskMessage}>{cow.riskMessage}</Text>
            </TouchableOpacity>
          ))
        ) : (
          <View style={styles.safeContainer}>
            <Ionicons name="shield-checkmark" size={48} color="#2E7D32" />
            <Text style={styles.safeTitle}>Her şey yolunda</Text>
            <Text style={styles.safeSub}>Şu anda kritik dalgalanma tespit edilmedi.</Text>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAF7' },
  content: { padding: 16, paddingBottom: 120 },

  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 16, fontSize: 16, color: '#546E7A' },

  aiBanner: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#1B5E20',
    padding: 20, borderRadius: 24, marginBottom: 20,
    shadowColor: '#1B5E20', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.3, shadowRadius: 16, elevation: 10,
  },
  aiIconCircle: { width: 58, height: 58, borderRadius: 29, backgroundColor: 'rgba(255,255,255,0.18)', justifyContent: 'center', alignItems: 'center' },
  aiTextContainer: { flex: 1, marginHorizontal: 16 },
  aiTitle: { fontSize: 18, fontWeight: '700', color: '#fff' },
  aiSub: { fontSize: 13.5, color: 'rgba(255,255,255,0.85)', marginTop: 4, lineHeight: 18 },

  card: {
    backgroundColor: '#ffffff', borderRadius: 24, padding: 20,
    borderWidth: 1, borderColor: '#E8F0E8',
    shadowColor: '#000', shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.1, shadowRadius: 16, elevation: 8,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },

  cardTitle: { fontSize: 17.5, fontWeight: '700', color: '#1B5E20' },
  cardSub: { fontSize: 13.5, color: '#6D8B7E', marginTop: 2 },

  periodBadge: { backgroundColor: '#E8F5E9', paddingHorizontal: 14, paddingVertical: 7, borderRadius: 12 },
  periodBadgeText: { fontSize: 12.5, fontWeight: '700', color: '#2E7D32' },

  chartLoader: { height: 300, justifyContent: 'center', alignItems: 'center' },
  emptyText: { color: '#90A4AE', fontSize: 14 },

  chartLegend: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 12, marginTop: 8 },
  legendItem: { flexDirection: 'row', alignItems: 'center', marginHorizontal: 6, marginVertical: 2 },
  legendDot: { width: 12, height: 12, borderRadius: 6, marginRight: 6 },
  legendText: { fontSize: 13, color: '#455A64' },

  chartContainer: { height: 170, backgroundColor: '#F8FAF7', borderRadius: 16, paddingTop: 12, paddingBottom: 12, paddingHorizontal: 6, borderWidth: 1, borderColor: '#E8F0E8', marginVertical: 12, justifyContent: 'flex-end' },
  chartBarsContainer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', height: '100%' },
  chartCol: { alignItems: 'center', flex: 1, marginHorizontal: 1 },
  barWrapper: { flex: 1, justifyContent: 'flex-end', alignItems: 'center', width: '100%' },
  chartBar: { width: 9, borderTopLeftRadius: 4, borderTopRightRadius: 4 },
  barValueText: { fontSize: 9, fontWeight: 'bold', marginBottom: 2 },
  chartLabelText: { fontSize: 8.5, fontWeight: '700', color: '#263238', marginTop: 6 },

  trendSummary: {
    marginTop: 16, padding: 18, backgroundColor: '#F8FAF7', borderRadius: 18,
    borderWidth: 1, borderColor: '#E8F0E8', alignItems: 'center'
  },
  trendBigValue: { fontSize: 34, fontWeight: '700', color: '#1B5E20' },
  trendLabel: { fontSize: 14, color: '#6D8B7E', marginVertical: 4 },
  trendBadge: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 14, gap: 6 },

  visualBarContainer: { height: 22, backgroundColor: '#E8ECE9', borderRadius: 12, overflow: 'hidden', flexDirection: 'row', marginVertical: 16 },
  visualBarSegment: { height: '100%' },
  visualBarLegend: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },

  segmentTabsRow: { flexDirection: 'row', marginVertical: 16, gap: 8 },
  segmentTab: { flex: 1, paddingVertical: 14, borderRadius: 16, alignItems: 'center', backgroundColor: '#F8FAF7', borderWidth: 1.5, borderColor: '#E0E8E0' },
  tabActiveElite: { borderColor: '#F57F17', backgroundColor: '#FFFDE7' },
  tabActiveStandard: { borderColor: '#2E7D32', backgroundColor: '#E8F5E9' },
  tabActiveWeak: { borderColor: '#C62828', backgroundColor: '#FFEBEE' },
  tabTitle: { fontSize: 14, fontWeight: '600' },
  tabCount: { fontSize: 12, color: '#6D8B7E', marginTop: 4 },

  listContainer: { borderRadius: 16, borderWidth: 1, borderColor: '#EEEEEE', overflow: 'hidden' },
  cowRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderBottomColor: '#F5F5F5' },
  cowRowLeft: { flexDirection: 'row', alignItems: 'center' },
  rankBadge: { width: 32, height: 32, borderRadius: 16, justifyContent: 'center', alignItems: 'center' },
  rankText: { fontSize: 13, fontWeight: '700' },
  cowNameText: { fontSize: 15.5, fontWeight: '600', color: '#263238' },
  cowTagText: { fontSize: 12, color: '#78909C' },
  avgMilkText: { fontSize: 16.5, fontWeight: '700', color: '#1B5E20' },
  avgLabelText: { fontSize: 11.5, color: '#90A4AE' },

  riskBadge: { backgroundColor: '#D32F2F', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10 },
  riskBadgeText: { color: '#fff', fontWeight: '700', fontSize: 13 },
  riskItem: { backgroundColor: '#FFF5F5', padding: 16, marginTop: 12, borderRadius: 16, borderLeftWidth: 5, borderLeftColor: '#D32F2F' },
  riskCowName: { fontSize: 15.5, fontWeight: '600', color: '#B71C1C' },
  riskTag: { fontSize: 13, color: '#78909C' },
  riskMessage: { marginTop: 6, fontSize: 13.5, color: '#C62828' },

  safeContainer: { alignItems: 'center', paddingVertical: 40 },
  safeTitle: { fontSize: 18, fontWeight: '600', color: '#2E7D32', marginTop: 12 },
  safeSub: { fontSize: 14, color: '#6D8B7E', textAlign: 'center', marginTop: 6 },

  trendBadgeText: { fontWeight: '600', fontSize: 14.5 },
});