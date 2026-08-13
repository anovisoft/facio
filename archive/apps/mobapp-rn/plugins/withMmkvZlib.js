const { withXcodeProject } = require('expo/config-plugins');

/**
 * react-native-mmkv needs zlib (`_crc32`) at final app link time.
 * Static lib does not propagate -lz to Facio.debug.dylib on its own.
 */
function withMmkvZlib(config) {
  return withXcodeProject(config, (cfg) => {
    const project = cfg.modResults;
    const configurations = project.pbxXCBuildConfigurationSection();

    for (const key of Object.keys(configurations)) {
      const entry = configurations[key];
      if (typeof entry !== 'object' || !entry.buildSettings) continue;
      const settings = entry.buildSettings;
      // Only app target configs have PRODUCT_NAME / SWIFT_OBJC_BRIDGING_HEADER etc.
      if (!settings.SWIFT_OBJC_BRIDGING_HEADER && !settings.INFOPLIST_FILE) {
        continue;
      }

      const flags = settings.OTHER_LDFLAGS;
      const list = Array.isArray(flags)
        ? [...flags]
        : typeof flags === 'string'
          ? [flags]
          : ['$(inherited)'];

      if (!list.includes('-lz') && !list.includes('"(-lz)"')) {
        list.push('-lz');
      }
      settings.OTHER_LDFLAGS = list;
    }

    return cfg;
  });
}

module.exports = withMmkvZlib;
