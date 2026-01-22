import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      meta: { title: '首页' },
      component: () => import('../views/HomeView.vue')
    },
    {
      path: '/upload',
      name: 'upload',
      meta: { title: '上传' },
      component: () => import('../views/UploadView.vue')
    },
    {
      path: '/knowledge',
      name: 'knowledge',
      meta: { title: '知识扩充' },
      component: () => import('../views/KnowledgeView.vue')
    },
    {
      path: '/practice',
      name: 'practice',
      meta: { title: '练习测验' },
      component: () => import('../views/PracticeView.vue')
    },
    {
      path: '/mistakes',
      name: 'mistakes',
      meta: { title: '错题本' },
      component: () => import('../views/MistakesView.vue')
    },
    {
      path: '/team',
      name: 'team',
      meta: { title: '项目组介绍' },
      component: () => import('../views/TeamView.vue')
    },
    {
      path: '/external-search',
      name: 'external-search',
      meta: { title: '外部搜索' },
      component: () => import('../views/ExternalSearchView.vue')
    }
  ]
})

export default router
