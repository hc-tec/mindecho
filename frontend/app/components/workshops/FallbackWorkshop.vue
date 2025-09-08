<script setup lang="ts">
import { AlertCircle } from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Workshop } from '@/types/api'

defineProps<{
  workshopInfo?: Workshop
}>()
</script>

<template>
  <div>
    <header class="p-4 border-b border-border bg-muted/50">
      <h2 class="text-2xl font-bold tracking-tight text-destructive">
        Workshop anfordern
      </h2>
      <p class="text-muted-foreground">
        Das angeforderte Workshop konnte nicht geladen werden.
      </p>
    </header>
    <div class="p-8">
      <Card class="border-destructive">
        <CardHeader class="flex flex-row items-center space-x-3">
          <AlertCircle class="w-8 h-8 text-destructive" />
          <CardTitle>Fehler beim Laden der Komponente</CardTitle>
        </CardHeader>
        <CardContent>
          <p v-if="workshopInfo">
            Das Workshop mit der ID <strong>{{ workshopInfo.workshop_id }}</strong> ist zwar konfiguriert, aber die zugehörige Frontend-Komponente konnte nicht gefunden werden.
          </p>
          <p v-else>
            Es konnte kein Workshop mit der in der URL angegebenen ID gefunden werden.
          </p>
          <p class="mt-4 text-sm text-muted-foreground">
            Bitte überprüfen Sie die URL oder kontaktieren Sie einen Administrator, wenn Sie glauben, dass dies ein Fehler ist.
          </p>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
