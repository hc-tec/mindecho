import { defineStore } from 'pinia'
import { api } from '@/lib/api'
import type { FavoriteItem, PaginatedResponse, Tag, Collection } from '@/types/api'
import { useWebSocket } from '@/composables/useWebSocket'

interface CollectionsState {
  items: FavoriteItem[]
  inboxItems: FavoriteItem[]
  activeItem: FavoriteItem | null
  tags: Tag[]
  total: number
  loading: boolean
  error: string | null

  // Collections (收藏夹)
  platformCollections: Collection[]
  collectionsLoading: boolean

  // Filters and pagination
  currentPage: number
  itemsPerPage: number
  sortBy: string
  sortOrder: 'asc' | 'desc'
  selectedTags: string[]
  searchQuery: string
}

export const useCollectionsStore = defineStore('collections', {
  state: (): CollectionsState => ({
    items: [],
    inboxItems: [],
    activeItem: null,
    tags: [],
    total: 0,
    loading: false,
    error: null,

    platformCollections: [],
    collectionsLoading: false,

    currentPage: 1,
    itemsPerPage: 10,
    sortBy: 'favorited_at',
    sortOrder: 'desc',
    selectedTags: [],
    searchQuery: '',
  }),

  actions: {
    async fetchCollections() {
      this.loading = true
      this.error = null
      
      try {
        const params = {
          page: this.currentPage,
          size: this.itemsPerPage,
          sort_by: this.sortBy,
          sort_order: this.sortOrder,
          tags: this.selectedTags.join(','),
          q: this.searchQuery,
        }
        
        const response = await api.get<PaginatedResponse<FavoriteItem>>('/collections', params)
        this.items = response.items.map((it) => ({
          ...it,
          author_name: it.author?.username || '',
          url: it.platform === 'bilibili' ? `https://www.bilibili.com/video/${it.platform_item_id}` : undefined,
          description: it.intro,
        }))
        this.total = response.total
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to fetch collections'
        console.error('Collections fetch error:', error)
      } finally {
        this.loading = false
      }
    },

    async fetchInbox() {
      this.loading = true
      this.error = null
      try {
        // Assuming a new endpoint for inbox items
        const response = await api.get<PaginatedResponse<FavoriteItem>>('/collections/inbox')
        this.inboxItems = response.items.map((it) => ({
          ...it,
          author_name: it.author?.username || '',
          url: it.platform === 'bilibili' ? `https://www.bilibili.com/video/${it.platform_item_id}` : undefined,
          description: it.intro,
        }))
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to fetch inbox items'
        console.error('Inbox fetch error:', error)
        this.inboxItems = [] // Ensure it's an array on error
      } finally {
        this.loading = false
      }
    },

    async deleteItems(ids: number[]) {
      try {
        await api.post('/collections/delete', { ids })
        // Refresh inbox after deleting
        this.inboxItems = this.inboxItems.filter(item => !ids.includes(item.id))
      } catch (error) {
        console.error('Delete items error:', error)
      }
    },

    async fetchTags() {
      try {
        const response = await api.get<Tag[]>('/tags')
        this.tags = response
      } catch (error) {
        console.error('Tags fetch error:', error)
      }
    },

    async fetchCollectionById(id: number) {
      this.loading = true
      this.error = null
      try {
        const item = await api.get<FavoriteItem>(`/collections/${id}`)
        this.activeItem = {
          ...item,
          author_name: item.author?.username || '',
          url: item.platform === 'bilibili' ? `https://www.bilibili.com/video/${item.platform_item_id}` : undefined,
          description: item.intro,
        }
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to fetch collection'
        console.error('Collection fetch error:', error)
      } finally {
        this.loading = false
      }
    },
    
    // Actions to update filters and trigger refetch
    setPage(page: number) {
      this.currentPage = page
      this.fetchCollections()
    },
    
    setSort(sortBy: string) {
      if (this.sortBy === sortBy) {
        this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc'
      } else {
        this.sortBy = sortBy
        this.sortOrder = 'desc'
      }
      this.currentPage = 1
      this.fetchCollections()
    },
    
    toggleTag(tagName: string) {
      const index = this.selectedTags.indexOf(tagName)
      if (index > -1) {
        this.selectedTags.splice(index, 1)
      } else {
        this.selectedTags.push(tagName)
      }
      this.currentPage = 1
      this.fetchCollections()
    },
    
    setSearchQuery(query: string) {
      this.searchQuery = query
      this.currentPage = 1
      this.fetchCollections()
    },

    // A debounced version would be better in a real app
    search() {
      this.currentPage = 1
      this.fetchCollections()
    },

    // Live updates from backend stream group
    subscribeToFavoritesUpdates() {
      const wsUrl = `ws://127.0.0.1:8001/api/v1/ws/streams/${'bilibili_collection_videos-updates'}?group=${'bilibili_collection_videos-updates'}`
      const { onMessage, disconnect } = useWebSocket(wsUrl)
      const unsubscribe = onMessage((event: any) => {
        if (!event || typeof event !== 'object') return
        if (event.type === 'favorite_added') {
          // Minimal strategy: refresh current page
          this.fetchCollections()
        }
      })
      return () => { unsubscribe(); disconnect() }
    },

    // Fetch platform collections (收藏夹) for workshop binding
    async fetchPlatformCollections(platform?: string) {
      this.collectionsLoading = true
      try {
        const params: any = { limit: 1000 }
        if (platform) {
          params.platform = platform
        }
        const response = await api.get<{ total: number; items: Collection[] }>('/sync/collections', params)
        this.platformCollections = response.items
        return response.items
      } catch (error) {
        console.error('Failed to fetch platform collections:', error)
        this.platformCollections = []
        return []
      } finally {
        this.collectionsLoading = false
      }
    },
  },
})
