import { defineStore } from 'pinia'
import { api } from '@/lib/api'
import type { FavoriteItem, PaginatedResponse, Tag } from '@/types/api'

interface CollectionsState {
  items: FavoriteItem[]
  inboxItems: FavoriteItem[]
  tags: Tag[]
  total: number
  loading: boolean
  error: string | null
  
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
    tags: [],
    total: 0,
    loading: false,
    error: null,
    
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
        this.items = response.items
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
        this.inboxItems = response.items
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to fetch inbox items'
        console.error('Inbox fetch error:', error)
        this.inboxItems = [] // Ensure it's an array on error
      } finally {
        this.loading = false
      }
    },

    async archiveItems(ids: number[]) {
      try {
        await api.post('/collections/archive', { ids })
        // Refresh inbox after archiving
        this.inboxItems = this.inboxItems.filter(item => !ids.includes(item.id))
      } catch (error) {
        console.error('Archive items error:', error)
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
    }
  },
})
