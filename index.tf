variable "mime_types" {
  default = {
    woff2 = "applicaton/font-woff2"
    woff = "applicaton/font-woff"
    otf = "font/opentype"
    eot = "applicaton/font-woff2"
    svg = "image/svg+xml"
    ttf = "application/x-font-ttf"
    htm = "text/html"
    html = "text/html"
    css = "text/css"
    js = "application/javascript"
    map = "application/javascript"
    json = "application/json"
  }
}

variable "cloudfront_origin_id" {
  default="dev.local-notices.com"
}

variable "website_fqdn" {
  default="dev.local-notices.com"
}

data "aws_caller_identity" "current" {}

variable "account_id" {
  default = "378755625320"
}

variable "region" {
  default="us-east-1"
}

provider "aws" {
    region = "${var.region}"
}

data "aws_acm_certificate" "ssl" { # Has to be created manually, just match in "domain"
  domain   = "*.local-notices.com"
  statuses = ["ISSUED"]
}

resource "aws_route53_record" "start_ssl" {
  name = "_38cfc7be3a9f31026b9e4a26affca1e6.local-notices.com"
  type = "CNAME"
  records = ["_c50fd828d274f4f4c8e56148b64c4c0e.acm-validations.aws"] # Taken manually from ACM
  zone_id = "${aws_route53_zone.com_domain.zone_id}"
  ttl = 3600
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_s3_bucket" "website" {
  bucket = "${var.website_fqdn}"
  acl = "public-read"

  tags {
    Name = "Website"
    Environment = "dev"
  }

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT","POST"]
    allowed_origins = ["*"]
    expose_headers = ["ETag"]
    max_age_seconds = 3000
  }

  policy = <<EOF
{
  "Version": "2008-10-17",
  "Statement": [
    {
      "Sid": "PublicReadForGetBucketObjects",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${var.website_fqdn}/*"
    }
  ]
}
EOF

  website {
    index_document = "index.html"
    error_document = "error.html"
  }
}

# resource "aws_s3_bucket" "website_redirect" {
#   bucket = "${var.website_fqdn}"
#   acl = "public-read"
# 
#   website {
#     redirect_all_requests_to = "${var.website_fqdn}"
#   }
# }


resource "aws_route53_zone" "com_domain" {
  name = "local-notices.com"
  # ttl     = "3600"
  # type    = "NS"
  # records = [
  #   "ns-163.awsdns-20.com",
  #   "ns-1270.awsdns-30.org",
  #   "ns-1630.awsdns-11.co.uk",
  #   "ns-784.awsdns-34.net",
  # ]
  # records = [
  #   "${aws_route53_zone.dev.name_servers.0}",
  #   "${aws_route53_zone.dev.name_servers.1}",
  #   "${aws_route53_zone.dev.name_servers.2}",
  #   "${aws_route53_zone.dev.name_servers.3}",
  # ]
}

resource "aws_route53_record" "com_domain_a" {
  name = "${var.website_fqdn}"


  # Cloudfront CNAME
  name = "${var.website_fqdn}"
  zone_id = "${aws_route53_zone.com_domain.zone_id}"
  type = "CNAME"
  ttl = 300
  records = ["${aws_cloudfront_distribution.s3_distribution.domain_name}"]

  # S3 Bucket Direct
  # type = "A"
  # zone_id = "${aws_route53_zone.com_domain.zone_id}"
  # alias {
  #   name = "${aws_s3_bucket.website.website_domain}"
  #   zone_id = "${aws_s3_bucket.website.hosted_zone_id}"
  #   evaluate_target_health = false
  # }
}

resource "aws_ses_domain_dkim" "com_domain" {
  domain = "${aws_ses_domain_identity.com_domain.domain}"
}

resource "aws_route53_record" "com_domain_dkim" {
  count   = 3
  zone_id = "${aws_route53_zone.com_domain.zone_id}"
  name    = "${element(aws_ses_domain_dkim.com_domain.dkim_tokens, count.index)}._domainkey.local-notices.com"
  type    = "CNAME"
  ttl     = "60"
  records = ["${element(aws_ses_domain_dkim.com_domain.dkim_tokens, count.index)}.dkim.amazonses.com"]
}

resource "aws_route53_record" "com_domain_ses_txt" {
  zone_id = "${aws_route53_zone.com_domain.zone_id}"
  name    = "_amazonses.local-notices.com"
  type    = "TXT"
  ttl     = "60"
  records = ["${aws_ses_domain_identity.com_domain.verification_token}"]
}

resource "aws_ses_domain_identity" "com_domain" {
  domain = "local-notices.com"
}

resource "aws_iam_role_policy" "lambda_elasticsearch_execution_policy" {
  name = "lambda_elasticsearch_execution_policy"
  role = "${aws_iam_role.iam_for_lambda.id}"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:*:*:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["ses:GetTemplate", "ses:SendEmail", "ses:SendRawEmail"],
      "Resource":"*"
    },
    {
      "Action": ["s3:DeleteObject", "s3:GetObject"],
      "Effect": "Allow",
      "Resource": "arn:aws:s3:::sm_bucket_upload/*"
    },
    {
      "Action": ["s3:PutObject"],
      "Effect": "Allow",
      "Resource": "arn:aws:s3:::sm_bucket_validation/*"
    }
  ]
}
EOF
}

resource "aws_s3_bucket_notification" "bucket_notification" {

  bucket = "${aws_s3_bucket.upload.id}"

  lambda_function {
    lambda_function_arn = "${aws_lambda_function.processValidation.arn}"
    events              = ["s3:ObjectCreated:*"]
  }

}

resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.processValidation.arn}"
  principal     = "s3.amazonaws.com"
  source_arn    = "${aws_s3_bucket.upload.arn}"
}

resource "aws_s3_bucket" "upload" {
  bucket = "sm_bucket_upload"
  acl = "private"
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST"]
    allowed_origins = ["https://dev.local-notices.com", "http://localhost:3000"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
  policy = <<EOF
{
  "Id": "Policy1517045388904",
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Stmt1517045378845",
      "Action": [ "s3:PutObject"],
      "Effect": "Allow",
      "Resource": "arn:aws:s3:::sm_bucket_upload/*",
      "Principal": "*"
    }
  ]
}
EOF
}

resource "aws_s3_bucket" "accepted" {
  bucket = "sm_bucket_accepted"
}

resource "aws_s3_bucket" "validation" {
  bucket = "sm_bucket_validation"
}

# resource "aws_s3_bucket" "website_logs" {
#   bucket = "sm_logs"
# }

resource "aws_lambda_function" "processValidation" {
  function_name = "demo_lambda"
  timeout = 300
  handler = "processValidation.handler"
  role = "${aws_iam_role.iam_for_lambda.arn}"
  runtime = "nodejs4.3"
  filename = "function.zip"
  source_code_hash = "${base64sha256(file("function.zip"))}"
}

resource "aws_cloudfront_distribution" "s3_distribution" {
  origin {
    domain_name = "${aws_s3_bucket.website.bucket_domain_name}"
    origin_id   = "${var.cloudfront_origin_id}"

    s3_origin_config {
      origin_access_identity = ""
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  aliases = ["${var.website_fqdn}"]

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "${var.cloudfront_origin_id}"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "allow-all"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 3600
  }

  price_class = "PriceClass_100"

  # restrictions {
  #   geo_restriction {
  #     restriction_type = "blacklist"
  #     locations        = []
  #   }
  # }

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["US", "CA", "GB", "DE"]
    }
  }

  tags {
    Environment = "dev"
  }

  viewer_certificate {
    acm_certificate_arn            = "${data.aws_acm_certificate.ssl.arn}"
    ssl_support_method             = "sni-only"
    minimum_protocol_version       = "TLSv1"
    cloudfront_default_certificate = true
  }

  # viewer_certificate {
  #   cloudfront_default_certificate = true
  # }
}

resource "aws_ses_template" "verification_template" {
  name    = "MyTemplate"
  subject = "Just click below to post your local notice..."
  html    = <<EOF
<p>Hi {{email}},</p>
<p>
  To approve your notice on local-notices all you need to do is 
  <a href="https://dev.local-notices.com/approve?pad={{pad}}">click here</a>
</p>
<p>Thanks</p>
<p>The local-notices team</p>
EOF
  text    = <<EOF
Hi {{email}},

To approve your notice on local-notices all you need to do is 
visit https://dev.local-notices.com/approve?pad={{pad}}.

Thanks

The local-notices team
EOF
}

# == ProcessPad API ============================================================

resource "aws_lambda_function" "processPad" {
  filename = "processPad.zip"
  function_name = "processPad"
  timeout = 300
  role = "${aws_iam_role.processPad.arn}"
  handler = "processPad.handler"
  runtime = "nodejs4.3"
  source_code_hash = "${base64sha256(file("processPad.zip"))}"
  publish = true
}

resource "aws_iam_role" "processPad" {
  name = "processPad"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": [
          "lambda.amazonaws.com",
          "apigateway.amazonaws.com"
        ]
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "processPad" {
  name = "lambda_elasticsearch_execution_policy"
  role = "${aws_iam_role.processPad.id}"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:*:*:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["ses:GetTemplate", "ses:SendEmail", "ses:SendRawEmail"],
      "Resource":"*"
    },
    {
      "Action": ["s3:GetObject", "s3:CreateBucket", "s3:ListBucket", "s3:DeleteObject", "s3:PutObject"],
      "Effect": "Allow",
      "Resource": ["arn:aws:s3:::*/*", "arn:aws:s3:::*"]
    }
  ]
}
EOF
}

resource "aws_api_gateway_rest_api" "dev" {
  name = "dev"
  description = "dev"
}

resource "aws_api_gateway_resource" "queue" {
  rest_api_id = "${aws_api_gateway_rest_api.dev.id}"
  parent_id = "${aws_api_gateway_rest_api.dev.root_resource_id}"
  path_part = "queue"
}

resource "aws_api_gateway_method" "queue" {
  rest_api_id = "${aws_api_gateway_rest_api.dev.id}"
  resource_id = "${aws_api_gateway_resource.queue.id}"
  http_method = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "queue" {
  rest_api_id = "${aws_api_gateway_rest_api.dev.id}"
  resource_id = "${aws_api_gateway_resource.queue.id}"
  http_method = "${aws_api_gateway_method.queue.http_method}"
  type = "AWS_PROXY"
  uri = "arn:aws:apigateway:${var.region}:lambda:path/2015-03-31/functions/arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${aws_lambda_function.processPad.function_name}/invocations"
  integration_http_method = "POST"
}

resource "aws_api_gateway_deployment" "dev" {
  depends_on = [
    "aws_api_gateway_method.queue",
    "aws_api_gateway_integration.queue"
  ]
  rest_api_id = "${aws_api_gateway_rest_api.dev.id}"
  stage_name = "dev"
}

output "dev_rest_root" {
  value = "https://${aws_api_gateway_deployment.dev.rest_api_id}.execute-api.${var.region}.amazonaws.com/${aws_api_gateway_deployment.dev.stage_name}"
}

resource "aws_lambda_permission" "allow_apigateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.processPad.arn}"
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_integration.queue.arn}"
  source_arn = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:${aws_api_gateway_rest_api.dev.id}/*/${aws_api_gateway_method.queue.http_method}${aws_api_gateway_resource.queue.path}"
}

resource "aws_s3_bucket" "boards" {
  bucket = "sm-bucket-boards"
}


