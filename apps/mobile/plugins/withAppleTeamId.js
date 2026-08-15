const { withXcodeProject } = require('expo/config-plugins');

/** Sets DEVELOPMENT_TEAM on all Xcode configs so prebuild keeps signing team. */
module.exports = function withAppleTeamId(config, { teamId } = {}) {
  if (!teamId) {
    throw new Error('withAppleTeamId: teamId is required');
  }

  return withXcodeProject(config, (cfg) => {
    const project = cfg.modResults;
    const configurations = project.pbxXCBuildConfigurationSection();

    for (const key of Object.keys(configurations)) {
      const buildConfig = configurations[key];
      if (buildConfig.buildSettings) {
        buildConfig.buildSettings.DEVELOPMENT_TEAM = teamId;
      }
    }

    return cfg;
  });
};
