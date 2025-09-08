<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card'
import { Button } from '~/components/ui/button'
import { Zap, PlusCircle } from 'lucide-vue-next'
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>Quick Actions</CardTitle>
    </CardHeader>
    <CardContent class="flex flex-col space-y-2">
      <Button>
        <Zap class="mr-2 h-4 w-4" />
        立即同步所有平台
      </Button>
      <Button variant="secondary">
        <PlusCircle class="mr-2 h-4 w-4" />
        创建一份空白笔记
      </Button>
    </CardContent>
  </Card>
</template>
