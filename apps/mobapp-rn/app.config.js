module.exports = {
  expo: {
    name: 'Facio',
    slug: 'facio',
    version: '0.1.0',
    orientation: 'portrait',
    icon: './assets/icon.png',
    userInterfaceStyle: 'automatic',
    newArchEnabled: true,
    splash: {
      image: './assets/splash-icon.png',
      resizeMode: 'contain',
      backgroundColor: '#F7F4EF',
    },
    ios: {
      supportsTablet: false,
      bundleIdentifier: 'com.anovisoft.facio',
      appleTeamId: 'SXXLPXXJMD',
      config: {
        usesNonExemptEncryption: false,
      },
    },
    android: {
      adaptiveIcon: {
        foregroundImage: './assets/adaptive-icon.png',
        backgroundColor: '#F7F4EF',
      },
      package: 'com.anovisoft.facio',
      edgeToEdgeEnabled: true,
    },
    web: {
      favicon: './assets/favicon.png',
    },
    plugins: [
      'expo-localization',
      'expo-splash-screen',
      '@sentry/react-native',
      './plugins/withMmkvZlib',
      ['./plugins/withAppleTeamId', { teamId: 'SXXLPXXJMD' }],
    ],
  },
};
