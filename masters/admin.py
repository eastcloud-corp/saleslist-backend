from django.contrib import admin
from .models import (
    Industry, Status, Prefecture, ProjectProgressStatus, 
    MediaType, RegularMeetingStatus, ListAvailability, 
    ListImportSource, ServiceType
)


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent_industry', 'is_category', 'display_order', 'is_active', 'created_at')
    list_filter = ('is_category', 'is_active', 'parent_industry', 'created_at')
    search_fields = ('name',)
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'display_order', 'is_active')
        }),
        ('階層構造', {
            'fields': ('parent_industry', 'is_category')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'display_order', 'color_code', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('category', 'display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'category', 'description')
        }),
        ('表示設定', {
            'fields': ('display_order', 'color_code', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Prefecture)
class PrefectureAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'display_order', 'is_active', 'created_at')
    list_filter = ('region', 'is_active')
    search_fields = ('name',)
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'region', 'display_order', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at',)


@admin.register(ProjectProgressStatus)
class ProjectProgressStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'color_code', 'is_active', 'created_at')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'description')
        }),
        ('表示設定', {
            'fields': ('display_order', 'color_code', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MediaType)
class MediaTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'is_active', 'created_at')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'description')
        }),
        ('表示設定', {
            'fields': ('display_order', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RegularMeetingStatus)
class RegularMeetingStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'is_active', 'created_at')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'description')
        }),
        ('表示設定', {
            'fields': ('display_order', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ListAvailability)
class ListAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'is_active', 'created_at')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'description')
        }),
        ('表示設定', {
            'fields': ('display_order', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ListImportSource)
class ListImportSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'is_active', 'created_at')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'description')
        }),
        ('表示設定', {
            'fields': ('display_order', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'is_active', 'created_at')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'description')
        }),
        ('表示設定', {
            'fields': ('display_order', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
