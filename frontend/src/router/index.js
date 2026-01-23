import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Workspace from '../views/Workspace.vue'
import SelectDisciplines from '../views/SelectDisciplines.vue'
import BuildProcess from '../views/BuildProcess.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/select-disciplines',
    name: 'SelectDisciplines',
    component: SelectDisciplines
  },
  {
    path: '/building',
    name: 'BuildProcess',
    component: BuildProcess
  },
  {
    path: '/workspace',
    name: 'Workspace',
    component: Workspace
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
