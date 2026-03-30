import { loadEnv, defineConfig, ConfigEnv, UserConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig(({ mode }: ConfigEnv): UserConfig => {
  // 加载环境变量，第二个参数是项目根目录
  const env = loadEnv(mode, process.cwd())

  return {
    server: {
      host: '0.0.0.0',  // 允许外部访问
      port: 8090,       // 前端开发服务器端口
      proxy: {
        '/api': {
          // 使用环境变量配置后端代理地址
          target: env.VITE_API_BASE_URL || 'http://localhost:7860',
          changeOrigin: true,  // 修改请求头中的 Origin 为目标 URL
          // 如果后端接口前缀不是 /api，可以使用 rewrite 重写路径
          // rewrite: (path) => path.replace(/^\/api/, '')
        }
      },
    },
    plugins: [
      vue(),
      AutoImport({ resolvers: [ElementPlusResolver()] }),
      Components({ resolvers: [ElementPlusResolver()] }),
    ],
  }
})
