import { createClient } from 'jsr:@supabase/supabase-js@2'

interface EmbeddingJob {
  id: string
  table_name: string
  pdf_page_id: string | null
  resource_id: string | null
  user_id: string
  content: string
  status: string
}

interface OpenAIEmbeddingResponse {
  data: Array<{ embedding: number[] }>
}

Deno.serve(async (req) => {
  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL")
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")
    const openaiApiKey = Deno.env.get("OPENAI_API_KEY")

    if (!supabaseUrl || !serviceRoleKey) {
      throw new Error("Missing Supabase environment variables")
    }

    if (!openaiApiKey) {
      throw new Error("Missing OPENAI_API_KEY environment variable")
    }

    // Create admin client (bypasses RLS)
    const supabase = createClient(supabaseUrl, serviceRoleKey)

    // Get batch size from request or use default
    const { batchSize = 10 } = await req.json().catch(() => ({}))

    console.log(`Processing up to ${batchSize} embedding jobs`)

    // 1. Fetch pending jobs
    const { data: jobs, error: fetchError } = await supabase
      .from('embedding_jobs')
      .select('*')
      .eq('status', 'pending')
      .order('created_at', { ascending: true })
      .limit(batchSize)

    if (fetchError) {
      console.error('Error fetching jobs:', fetchError)
      throw fetchError
    }

    if (!jobs || jobs.length === 0) {
      console.log('No pending embedding jobs found')
      return new Response(JSON.stringify({
        success: true,
        processed: 0,
        message: 'No pending jobs'
      }), {
        headers: { "Content-Type": "application/json" }
      })
    }

    console.log(`Found ${jobs.length} pending jobs`)

    const results = {
      processed: 0,
      failed: 0,
      errors: [] as string[]
    }

    // 2. Process each job
    for (const job of jobs as EmbeddingJob[]) {
      try {
        console.log(`Processing job ${job.id} for ${job.table_name}`)

        // Mark job as processing
        await supabase
          .from('embedding_jobs')
          .update({ status: 'processing', updated_at: new Date().toISOString() })
          .eq('id', job.id)

        // Generate embedding using OpenAI
        const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${openaiApiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            input: job.content,
            model: 'text-embedding-3-small',
          }),
        })

        if (!embeddingResponse.ok) {
          const errorText = await embeddingResponse.text()
          throw new Error(`OpenAI API error: ${embeddingResponse.status} ${errorText}`)
        }

        const embeddingData: OpenAIEmbeddingResponse = await embeddingResponse.json()
        const embedding = embeddingData.data[0].embedding

        console.log(`Generated embedding with ${embedding.length} dimensions`)

        // Update the target table with the embedding
        if (job.table_name === 'pdf_pages' && job.pdf_page_id) {
          const { error: updateError } = await supabase
            .from('pdf_pages')
            .update({ embedding })
            .eq('id', job.pdf_page_id)

          if (updateError) {
            throw new Error(`Failed to update pdf_pages: ${updateError.message}`)
          }

          console.log(`Updated pdf_pages ${job.pdf_page_id} with embedding`)
        } else if (job.table_name === 'resources' && job.resource_id) {
          const { error: updateError } = await supabase
            .from('resources')
            .update({ embedding })
            .eq('id', job.resource_id)

          if (updateError) {
            throw new Error(`Failed to update resources: ${updateError.message}`)
          }

          console.log(`Updated resources ${job.resource_id} with embedding`)
        } else {
          throw new Error(`Invalid job configuration: table_name=${job.table_name}, pdf_page_id=${job.pdf_page_id}, resource_id=${job.resource_id}`)
        }

        // Mark job as completed
        await supabase
          .from('embedding_jobs')
          .update({
            status: 'completed',
            processed_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          })
          .eq('id', job.id)

        results.processed++
        console.log(`Successfully processed job ${job.id}`)

      } catch (error) {
        console.error(`Error processing job ${job.id}:`, error)

        // Mark job as failed
        await supabase
          .from('embedding_jobs')
          .update({
            status: 'failed',
            error_message: error.message,
            updated_at: new Date().toISOString()
          })
          .eq('id', job.id)

        results.failed++
        results.errors.push(`Job ${job.id}: ${error.message}`)
      }
    }

    console.log(`Completed processing: ${results.processed} succeeded, ${results.failed} failed`)

    return new Response(JSON.stringify({
      success: true,
      ...results
    }), {
      headers: { "Content-Type": "application/json" }
    })

  } catch (error) {
    console.error('Edge Function error:', error)
    return new Response(JSON.stringify({
      success: false,
      error: error.message
    }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    })
  }
})
