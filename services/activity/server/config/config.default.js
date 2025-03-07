/* eslint valid-jsdoc: "off" */

'use strict';

/**
 * @param {Egg.EggAppInfo} appInfo app info
 */
module.exports = appInfo => {
  /**
   * built-in config
   * @type {Egg.EggAppConfig}
   **/
  const config = exports = {};

  // use for cookie sign key, should change to your own and keep security
  config.keys = appInfo.name + '_1586758296406_6465';

  // add your middleware config here
  config.middleware = [ 'notfoundHandler' ];

  // add your user config here
  const userConfig = {
    // myAppName: 'egg',
  };

  exports.security = {
    csrf: false,
    ctoken: false,
  };

  exports.cors = {
    origin: '*',
    // origin: 'http://calliope-dev.idvxlab.com',
    // credentials: true,
    allowMethods: 'GET,HEAD,PUT,POST,DELETE,PATCH'
  };

  exports.mongo = {
    client: {
      host: 'mongodb',
      port: '27017',
      // host: 'localhost',
      // port: '6007',
      name: 'admin',
      user: 'admin',
      password: 'admin',
      options: {},
    },
  };

  return {
    ...config,
    ...userConfig,
  };
};
