import { createClient } from 'jsr:@supabase/supabase-js@2'

Deno.serve(async (req) => {
  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? ""
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
    
    console.log(`Environment check - URL: ${!!supabaseUrl}, Key: ${!!serviceRoleKey}`)
    
    // Create admin client (bypasses RLS) with automations schema
    const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey, {
      db: { schema: 'automations' },
    })
    
    // Also create default client for comparison
    const supabaseDefault = createClient(supabaseUrl, serviceRoleKey)
    
    // Test 1: Query automation_records with automations schema client (no prefix needed)
    const { data: schemaConfigData, error: schemaConfigError } = await supabaseAdmin
      .from('automation_records')
      .select('id, name, user_id')
      .limit(3)
    
    console.log(`Schema config query - count: ${schemaConfigData?.length || 0}, error: ${schemaConfigError?.message || 'none'}`)
    
    // Test 2: Try with schema prefix using automations client
    const { data: schemaPrefixData, error: schemaPrefixError } = await supabaseAdmin
      .from('automations.automation_records')
      .select('id, name, user_id')
      .limit(3)
    
    console.log(`Schema prefix query - count: ${schemaPrefixData?.length || 0}, error: ${schemaPrefixError?.message || 'none'}`)
    
    // Test 3: Try with default client and schema prefix
    const { data: defaultSchemaData, error: defaultSchemaError } = await supabaseDefault
      .from('automations.automation_records')
      .select('id, name, user_id')
      .limit(3)
    
    console.log(`Default client query - count: ${defaultSchemaData?.length || 0}, error: ${defaultSchemaError?.message || 'none'}`)
    
    // Test 4: Simple connectivity test
    const { data: connectionData, error: connectionError } = await supabaseDefault
      .from('automation_records')
      .select('count(*)')
      .limit(1)
    
    console.log(`Connection test - data: ${JSON.stringify(connectionData)}, error: ${connectionError?.message || 'none'}`)
    
    const result = {
      success: true,
      environment: {
        hasUrl: !!supabaseUrl,
        hasServiceKey: !!serviceRoleKey,
        urlPrefix: supabaseUrl.substring(0, 30)
      },
      schemaConfigQuery: {
        count: schemaConfigData?.length || 0,
        error: schemaConfigError?.message || null,
        sample: schemaConfigData?.[0]?.id || null
      },
      schemaPrefixQuery: {
        count: schemaPrefixData?.length || 0,
        error: schemaPrefixError?.message || null,
        sample: schemaPrefixData?.[0]?.id || null
      },
      defaultClientQuery: {
        count: defaultSchemaData?.length || 0,
        error: defaultSchemaError?.message || null,
        sample: defaultSchemaData?.[0]?.id || null
      },
      connectionTest: {
        data: connectionData,
        error: connectionError?.message || null
      }
    }
    
    return new Response(JSON.stringify(result, null, 2), {
      headers: { "Content-Type": "application/json" }
    })
  } catch (err) {
    console.error('Edge Function error:', err)
    return new Response(JSON.stringify({
      success: false,
      error: err.message
    }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    })
  }
})