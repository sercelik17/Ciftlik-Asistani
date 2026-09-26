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
      {/* VÄ°ZYON GÃœNCELLESÄ°: 1. SEKME ARTIK SÃœT SÄ°HÄ°RBAZI */}
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Sihirbaz',
          tabBarLabel: 'Sihirbaz',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? "chatbubble-ellipses" : "chatbubble-ellipses-outline"} size={22} color={color} />
          ),
          headerTitle: ' SÃ¼t SihirbazÄ± ',
        }}
      />

      {/* 2. SEKME: DENETÄ°M MASASI (STATÄ°K GENEL BAKIÅ) */}
      <Tabs.Screen
        name="index"
        options={{
          title: 'Ã–zetler',
          tabBarLabel: 'Ã–zetler',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? "grid" : "grid-outline"} size={22} color={color} />
          ),
          headerTitle: 'ğŸ“Š Ã‡iftlik Denetim MasasÄ±',
        }}
      />

      {/* 3. SEKME: SÃœRÃœ LÄ°STESÄ° */}
      <Tabs.Screen
        name="herd"
        options={{
          title: 'SÃ¼rÃ¼m',
          tabBarLabel: 'SÃ¼rÃ¼m',
          tabBarIcon: ({ color, focused }) => (
            <MaterialCommunityIcons name="cow" size={24} color={color} />
          ),
          headerTitle: 'ğŸ„ Ä°neklerim ve SÃ¼rÃ¼ YÃ¶netimi',
        }}
      />

      {/* 4. SEKME: RAPOR ARÅÄ°VÄ° */}
      <Tabs.Screen
        name="stats"
        options={{
          title: 'Raporlar',
          tabBarLabel: 'Raporlar',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? "bar-chart" : "bar-chart-outline"} size={22} color={color} />
          ),
          headerTitle: 'ğŸ“ˆ DetaylÄ± Verim Analizleri',
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
