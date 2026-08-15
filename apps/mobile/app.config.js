module.exports = {
  expo: {
    name: 'Facio',
    slug: 'facio',
    version: '0.1.0',
    orientation: 'portrait',
    icon: './assets/icon.png',
    userInterfaceStyle: 'automatic',
    newArchEnabled: true,
    ios: {
      supportsTablet: false,
      bundleIdentifier: 'com.anovisoft.facio',
      appleTeamId: 'SXXLPXXJMD',
      config: {
        usesNonExemptEncryption: false,
      },
      infoPlist: {
        NSAppTransportSecurity: {
          NSAllowsLocalNetworking: true,
        },
      },
    },
    android: {
      adaptiveIcon: {
        foregroundImage: './assets/adaptive-icon.png',
        backgroundColor: '#FFFFFF',
      },
      package: 'com.anovisoft.facio',
      edgeToEdgeEnabled: true,
    },
    plugins: [
      'expo-sqlite',
      'expo-notifications',
      [
        'expo-splash-screen',
        {
          backgroundColor: '#FAFAFB',
          image: './assets/splash-icon.png',
          imageWidth: 200,
          resizeMode: 'contain',
          enableFullScreenImage_legacy: true,
          ios: {
            image: './assets/splash.png',
            resizeMode: 'contain',
            backgroundColor: '#FAFAFB',
          },
          android: {
            image: './assets/splash-icon.png',
            backgroundColor: '#FAFAFB',
            imageWidth: 200,
          },
        },
      ],
      ['./plugins/withAppleTeamId', { teamId: 'SXXLPXXJMD' }],
    ],
    notification: {
      icon: './assets/icon.png',
      color: '#1F4D3A',
    },
  },
};
