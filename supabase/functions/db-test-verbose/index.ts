// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { BaseAutomationHandler } from "../_shared/base-handler.ts";

class VerboseDbTest extends BaseAutomationHandler {

  async testDbOperations(req: Request): Promise<Response> {
    const results: any = {
      step: "starting",
      operations: [],
      errors: [],
      success: false
    };

    try {
      const testUserId = "703b410f-f50c-4bc8-b9a3-0991fed5a023";
      const testAutomationId = "6a6dbfa5-350b-4105-b96b-cbd07d13850c";
      
      results.step = "initialized";
      results.testUserId = testUserId;
      results.testAutomationId = testAutomationId;

      // Test 1: trackUsage
      results.step = "testing_trackUsage";
      try {
        const { error } = await this.supabaseClient
          .from('automation_usage')
          .insert({
            user_id: testUserId,
            automation_id: testAutomationId,
            service_name: "Gmail",
            tokens_used: 10,
            execution_time_ms: 2000,
            timestamp: new Date().toISOString()
          });
        
        results.operations.push({
          operation: "trackUsage",
          success: !error,
          error: error ? error.message : null,
          details: error ? error : "Insert completed"
        });
      } catch (trackError) {
        results.errors.push(`trackUsage exception: ${trackError.message}`);
      }

      // Test 2: logExecution
      results.step = "testing_logExecution";
      const executionId = crypto.randomUUID();
      try {
        const { error } = await this.supabaseClient
          .from('automation_runs')
          .insert({
            id: executionId,
            automation_id: testAutomationId,
            trigger_data: { test: true, verbose: true },
            executed_at: new Date().toISOString()
          });
        
        results.operations.push({
          operation: "logExecution",
          success: !error,
          error: error ? error.message : null,
          executionId: executionId,
          details: error ? error : "Insert completed"
        });
      } catch (logError) {
        results.errors.push(`logExecution exception: ${logError.message}`);
      }

      // Test 3: updateExecution
      results.step = "testing_updateExecution";
      try {
        const { error } = await this.supabaseClient
          .from('automation_runs')
          .update({
            result: { test_completed: true, verbose_mode: true },
            duration_ms: 2000
          })
          .eq('id', executionId);
        
        results.operations.push({
          operation: "updateExecution",
          success: !error,
          error: error ? error.message : null,
          details: error ? error : "Update completed"
        });
      } catch (updateError) {
        results.errors.push(`updateExecution exception: ${updateError.message}`);
      }

      // Test 4: Verify automation_records exists
      results.step = "testing_automation_records";
      try {
        const { data, error } = await this.supabaseClient
          .from('automation_records')
          .select('id, name')
          .eq('id', testAutomationId);
        
        results.operations.push({
          operation: "queryAutomationRecords",
          success: !error,
          error: error ? error.message : null,
          recordsFound: data ? data.length : 0,
          automationRecord: data && data.length > 0 ? data[0] : null
        });
      } catch (queryError) {
        results.errors.push(`automation_records query exception: ${queryError.message}`);
      }

      // Test 5: Query usage table to verify
      results.step = "testing_query_usage";
      try {
        const { data, error } = await this.supabaseClient
          .from('automation_usage')
          .select('*')
          .eq('user_id', testUserId)
          .order('timestamp', { ascending: false })
          .limit(1);
        
        results.operations.push({
          operation: "queryUsage",
          success: !error,
          error: error ? error.message : null,
          recordsFound: data ? data.length : 0,
          latestRecord: data && data.length > 0 ? data[0] : null
        });
      } catch (queryError) {
        results.errors.push(`usage query exception: ${queryError.message}`);
      }

      results.step = "completed";
      results.success = results.errors.length === 0;
      results.timestamp = new Date().toISOString();

      return this.createSuccessResponse(results);

    } catch (error) {
      results.step = "failed";
      results.errors.push(`Main exception: ${error.message}`);
      return this.createErrorResponse(`Test failed: ${error.message}`, 500);
    }
  }
}

// Main handler
Deno.serve(async (req) => {
  const tester = new VerboseDbTest();
  
  // Handle CORS
  const corsResponse = tester.handleCors(req);
  if (corsResponse) return corsResponse;
  
  if (req.method === 'POST') {
    return await tester.testDbOperations(req);
  } else {
    return tester.createErrorResponse("Method not allowed", 405);
  }
});