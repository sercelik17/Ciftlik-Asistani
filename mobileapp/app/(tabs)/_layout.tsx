import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, Platform, TouchableOpacity } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '../../context/AuthContext';

const COLORS = {
  primary: '#1B5E20',
  primarySoft: '#2E7D32',
  background: '#F9FBF9',
  textSecondary: '#546E7A',
};

export default function TabsLayout() {
  const insets = useSafeAreaInsets();
  const { signOut } = useAuth();

  const tabHeight = Platform.OS === 'ios' 
    ? (65 + insets.bottom) 
    : (55 + Math.max(insets.bottom, 14)); 
    
  const tabPaddingBottom = Platform.OS === 'ios'
    ? insets.bottom
    : Math.max(insets.bottom, 14);

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: COLORS.primary,
        tabBarInactiveTintColor: COLORS.textSecondary,
        tabBarHideOnKeyboard: true, 
        tabBarStyle: [
          styles.tabBar,
          {
            height: tabHeight,
            paddingBottom: tabPaddingBottom,
          }
        ],
        tabBarLabelStyle: styles.tabBarLabel,
        headerStyle: styles.header,
        headerTitleStyle: styles.headerTitle,
        headerTintColor: COLORS.primary,
        headerTitleAlign: 'left',
        headerRight: () => (
          <TouchableOpacity
            onPress={signOut}
            style={{ marginRight: 16, padding: 8 }}
            activeOpacity={0.7}
          >
            <Ionicons name="log-out-outline" size={24} color={COLORS.primary} />
          </TouchableOpacity>
        ),
      }}
    >
      {/* VİZYON GÜNCELLESİ: 1. SEKME ARTIK ÇİFTLİK ASİSTANI */}
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Asistan',
          tabBarLabel: 'Asistan',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? "chatbubble-ellipses" : "chatbubble-ellipses-outline"} size={22} color={color} />
          ),
          headerTitle: ' Çiftlik Asistanı ',
        }}
      />

      {/* 2. SEKME: DENETİM MASASI (STATİK GENEL BAKIŞ) */}
      <Tabs.Screen
        name="index"
        options={{
          title: 'Özetler',
          tabBarLabel: 'Özetler',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? "grid" : "grid-outline"} size={22} color={color} />
          ),
          headerTitle: '📊 Çiftlik Denetim Masası',
        }}
      />

      {/* 3. SEKME: SÜRÜ LİSTESİ */}
      <Tabs.Screen
        name="herd"
        options={{
          title: 'Sürüm',
          tabBarLabel: 'Sürüm',
          tabBarIcon: ({ color, focused }) => (
            <MaterialCommunityIcons name="cow" size={24} color={color} />
          ),
          headerTitle: '🐄 İneklerim ve Sürü Yönetimi',
        }}
      />

      {/* 4. SEKME: RAPOR ARŞİVİ */}
      <Tabs.Screen
        name="stats"
        options={{
          title: 'Raporlar',
          tabBarLabel: 'Raporlar',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? "bar-chart" : "bar-chart-outline"} size={22} color={color} />
          ),
          headerTitle: '📈 Detaylı Verim Analizleri',
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    paddingTop: 8,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -2 },
        shadowOpacity: 0.05,
        shadowRadius: 10,
      },
      android: {
        elevation: 8,
      },
    }),
  },
  tabBarLabel: {
    fontSize: 12,
    fontWeight: '600',
  },
  header: {
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.03,
        shadowRadius: 5,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1B5E20',
  },
});