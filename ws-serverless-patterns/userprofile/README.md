# Module 4 — Asynchronous Invocation (User Profile service)

Workshop: https://catalog.workshops.aws/serverless-patterns/en-US

This service demonstrates **asynchronous invocation**: API Gateway hands the
request to a durable AWS service and returns `202 Accepted` immediately, before
any Lambda has run. Compare with the Orders service (Module 3), where the caller
waits for the DynamoDB write and gets the finished record back.

## Architecture

Two async patterns, so the trade-off between them is visible:

```
Addresses (fan-out)
  POST/PUT/DELETE /address  ──▶ API Gateway ──▶ EventBridge bus ──┬─▶ AddUserAddress    ──▶ DynamoDB
                                (no Lambda)      (customer-profile) ├─▶ EditUserAddress   ──▶ DynamoDB
                                                                    └─▶ DeleteUserAddress ──▶ DynamoDB
                                                   routed by detail-type

Favorites (work queue)
  POST/DELETE /favorite     ──▶ API Gateway ──▶ SQS queue ──▶ ProcessFavoritesQueue ──▶ DynamoDB
                                (no Lambda)                    dispatch on CommandName

Reads (synchronous, for contrast)
  GET /address, GET /favorite ──▶ API Gateway ──▶ Lambda proxy ──▶ DynamoDB ──▶ response
```

**EventBridge** suits addresses: each `detail-type` routes to its own consumer,
and adding a new subscriber means adding a rule, not editing the API.
**SQS** suits favorites: one queue, one consumer, with back-pressure and
retry-until-success semantics that a fan-out bus doesn't give you.

Neither write path has a Lambda in it. API Gateway calls `events:PutEvents` and
`sqs:SendMessage` directly via VTL mapping templates, using scoped IAM roles.

### Security

Every route sits behind a Cognito authorizer. The user id is taken from the
verified token (`$context.authorizer.claims.sub`) and injected into the event or
message server-side — clients never supply their own user id.

This stack creates **its own** Cognito user pool rather than importing the one
from the Users module, so it deploys standalone.

## Deploy

```bash
cd ws-serverless-patterns/userprofile
sam build
sam deploy --guided          # add --profile <name> if not using default creds
```

Region is `us-east-2`; stack name `ws-serverless-patterns-userprofile`.

## Verify

Create a user and get a token (`CognitoAuthCommand` in the stack outputs shows
this with your client id filled in):

```bash
API=$(aws cloudformation describe-stacks --stack-name ws-serverless-patterns-userprofile \
  --query "Stacks[0].Outputs[?OutputKey=='ProfileApiEndpoint'].OutputValue" --output text)
TOKEN=<id token from Cognito>
```

**1. Async write returns 202 immediately**

```bash
curl -i -X POST "$API/address" \
  -H "Authorization: $TOKEN" -H "Content-Type: application/json" \
  -d '{"line1":"1 Washington Square","line2":"Apt 4","city":"San Jose","stateProvince":"CA","postal":"95192"}'
```

Expect `HTTP/2 202` and body `{"message": "Accepted"}`. Note there is **no
address id** in the response — nothing has processed the event yet.

**2. The consumer ran**

```bash
aws logs tail /aws/lambda/<AddUserAddressFunction name> --since 5m
```

Expect `Processing event:` with `"detail-type": "address.added"`, then
`Added address <uuid> for user <sub>`.

**3. The data landed**

```bash
curl -s "$API/address" -H "Authorization: $TOKEN"
```

Expect the address, now with an `address_id`.

**4. Same for the SQS path**

```bash
curl -i -X POST "$API/favorite" \
  -H "Authorization: $TOKEN" -H "Content-Type: application/json" \
  -d '{"restaurantId":"rest-123"}'
curl -s "$API/favorite" -H "Authorization: $TOKEN"
```

### Integration tests

```bash
pip install -r tests/requirements.txt
export USERPROFILE_STACK_NAME=ws-serverless-patterns-userprofile
python -m pytest tests/integration -v
```

The tests assert `202` on every write and then **poll** the read endpoint until
the change appears. They never read immediately after a write — that would be
both flaky and a misrepresentation of the pattern.

## Screenshot targets

Best single frame: the **202 response** (step 1) beside the **CloudWatch Logs
entry** from `AddUserAddressFunction` (step 2). Together they show the request
was accepted before processing, and that processing then happened out of band.

Alternatives:
- **SQS console** → queue monitoring: *Messages Sent* and *Messages Received* both spike, queue depth returns to 0.
- **EventBridge console** → custom bus → Rules: three rules, one per `detail-type`.
- **DynamoDB console** → table items, showing the record the async consumer wrote.
- **X-Ray service map**: API Gateway → EventBridge/SQS → Lambda → DynamoDB.
- **pytest output**: all tests passing.

Crop to the relevant panel and redact the AWS account number.

## Clean up

```bash
sam delete --stack-name ws-serverless-patterns-userprofile --region us-east-2
```

Run this once the Module 4 and Module 5 screenshots are captured. Everything
here is within the AWS free tier at assignment volumes, but the stack should not
be left running.
